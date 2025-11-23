"""
Cloudflare protection middleware - blocks direct access to Cloud Run
Only allows requests from Cloudflare (reporting.dabronet.pl)
"""
import logging
import ipaddress
from flask import request, abort
from app.config import Config
import requests
from functools import lru_cache

logger = logging.getLogger(__name__)

# Cache Cloudflare IP ranges
_CLOUDFLARE_IPS = None


@lru_cache(maxsize=1)
def get_cloudflare_ips():
    """Get Cloudflare IP ranges (cached)"""
    global _CLOUDFLARE_IPS
    if _CLOUDFLARE_IPS is None:
        try:
            response = requests.get(Config.CLOUDFLARE_IPS_URL, timeout=5)
            if response.status_code == 200:
                _CLOUDFLARE_IPS = [ipaddress.ip_network(ip.strip()) for ip in response.text.strip().split('\n') if ip.strip()]
                logger.info(f"Loaded {len(_CLOUDFLARE_IPS)} Cloudflare IP ranges")
            else:
                logger.warning("Could not fetch Cloudflare IP ranges")
                _CLOUDFLARE_IPS = []
        except Exception as e:
            logger.warning(f"Error fetching Cloudflare IP ranges: {e}")
            _CLOUDFLARE_IPS = []
    return _CLOUDFLARE_IPS


def is_cloudflare_ip(client_ip: str) -> bool:
    """Check if client IP is from Cloudflare"""
    if not client_ip:
        return False
    
    try:
        client_ip_obj = ipaddress.ip_address(client_ip)
        cloudflare_ips = get_cloudflare_ips()
        return any(client_ip_obj in network for network in cloudflare_ips)
    except ValueError:
        # Invalid IP address
        return False


def check_cloudflare_protection():
    """
    Check if request is from Cloudflare.
    Returns True if allowed, False if blocked.
    """
    from app.config import Config
    
    # Skip protection if disabled
    if not Config.REQUIRE_CLOUDFLARE:
        return True
    
    # Get client IP
    client_ip = request.headers.get('CF-Connecting-IP')  # Cloudflare adds this
    if not client_ip:
        # Try to get from X-Forwarded-For (Cloud Run adds this)
        forwarded_for = request.headers.get('X-Forwarded-For')
        if forwarded_for:
            client_ip = forwarded_for.split(',')[0].strip()
        else:
            client_ip = request.remote_addr
    
    # Check Host header
    host = request.headers.get('Host', '')
    allowed_hosts = Config.ALLOWED_HOSTS
    
    # Check if Host is allowed
    host_allowed = any(allowed_host.lower() in host.lower() for allowed_host in allowed_hosts)
    
    # Check if request comes from Cloudflare
    # Method 1: Check CF-Connecting-IP header (most reliable)
    has_cf_header = request.headers.get('CF-Connecting-IP') is not None
    has_cf_ray = request.headers.get('CF-Ray') is not None
    
    # Method 2: Check if IP is in Cloudflare ranges
    is_cf_ip = is_cloudflare_ip(client_ip)
    
    # Allow if:
    # 1. Has Cloudflare headers (CF-Connecting-IP or CF-Ray) AND host is allowed
    # 2. OR IP is in Cloudflare ranges AND host is allowed
    is_from_cloudflare = (has_cf_header or has_cf_ray) or is_cf_ip
    
    if not is_from_cloudflare:
        logger.warning(f"Blocked direct access attempt from {client_ip} (Host: {host})")
        return False
    
    if not host_allowed:
        logger.warning(f"Blocked request with invalid Host header: {host} (allowed: {allowed_hosts})")
        return False
    
    return True


def cloudflare_protection_middleware():
    """
    Flask middleware to protect against direct access.
    Add this as @app.before_request
    """
    # Allow health checks
    if request.path in ['/health', '/ready']:
        return None
    
    # Check Cloudflare protection
    if not check_cloudflare_protection():
        logger.warning(f"Blocked unauthorized access: {request.method} {request.path} from {request.remote_addr}")
        abort(403, description="Access denied. This service is only accessible through Cloudflare.")
    
    return None

