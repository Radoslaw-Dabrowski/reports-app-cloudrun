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
        logger.debug("Cloudflare protection disabled")
        return True
    
    # Get Host header
    host = request.headers.get('Host', '')
    allowed_hosts = Config.ALLOWED_HOSTS
    
    # Check if Host is allowed
    host_allowed = any(allowed_host.lower() in host.lower() for allowed_host in allowed_hosts)
    
    # Get client IP for logging
    client_ip = request.headers.get('CF-Connecting-IP')
    if not client_ip:
        forwarded_for = request.headers.get('X-Forwarded-For')
        if forwarded_for:
            client_ip = forwarded_for.split(',')[0].strip()
        else:
            client_ip = request.remote_addr
    
    # Check if request comes from Cloudflare
    # Method 1: Check CF-Connecting-IP header (most reliable - Cloudflare always adds this)
    has_cf_connecting_ip = request.headers.get('CF-Connecting-IP') is not None
    has_cf_ray = request.headers.get('CF-Ray') is not None
    has_cf_country = request.headers.get('CF-IPCountry') is not None
    
    # Method 2: Check if IP is in Cloudflare ranges (fallback)
    is_cf_ip = is_cloudflare_ip(client_ip)
    
    # Log for debugging
    logger.debug(f"Protection check - Host: {host}, CF-Connecting-IP: {has_cf_connecting_ip}, CF-Ray: {has_cf_ray}, CF-Country: {has_cf_country}, Client IP: {client_ip}")
    
    # STRICT MODE: Require BOTH Cloudflare headers AND correct Host
    # Primary check: Cloudflare headers (most reliable)
    has_cloudflare_headers = has_cf_connecting_ip or has_cf_ray or has_cf_country
    
    # If we have Cloudflare headers, allow if host is correct
    if has_cloudflare_headers:
        if host_allowed:
            logger.debug(f"Allowed: Request from Cloudflare with valid Host ({host})")
            return True
        else:
            logger.warning(f"Blocked: Cloudflare request but invalid Host ({host}, allowed: {allowed_hosts})")
            return False
    
    # Fallback: Check IP ranges (less reliable but works if headers are missing)
    if is_cf_ip:
        if host_allowed:
            logger.debug(f"Allowed: Request from Cloudflare IP range with valid Host ({host})")
            return True
        else:
            logger.warning(f"Blocked: Cloudflare IP but invalid Host ({host}, allowed: {allowed_hosts})")
            return False
    
    # Block direct Cloud Run URLs immediately (even if they have correct Host header)
    if 'run.app' in host or 'cloudfunctions.net' in host:
        logger.warning(f"Blocked: Direct Cloud Run access detected (Host: {host}, IP: {client_ip})")
        return False
    
    # If no Cloudflare indicators and host is not allowed, block
    if not host_allowed:
        logger.warning(f"Blocked: No Cloudflare indicators and invalid Host ({host}, allowed: {allowed_hosts}, IP: {client_ip})")
        return False
    
    # STRICT: If host is allowed but no Cloudflare indicators, block
    # This ensures that only requests from Cloudflare (with headers) are allowed
    # Even if Host header is correct, we require Cloudflare headers for security
    if host_allowed:
        logger.warning(f"Blocked: Valid Host ({host}) but missing Cloudflare headers (IP: {client_ip}). Worker may not be configured correctly.")
        return False
    
    # Default: block
    logger.warning(f"Blocked: No valid indicators (Host: {host}, IP: {client_ip})")
    return False


def cloudflare_protection_middleware():
    """
    Flask middleware to protect against direct access.
    Add this as @app.before_request
    """
    # Allow health checks (but still check Cloudflare for /ready)
    if request.path == '/health':
        return None
    
    # Check Cloudflare protection
    try:
        if not check_cloudflare_protection():
            logger.warning(f"Blocked unauthorized access: {request.method} {request.path} from {request.remote_addr} (Host: {request.headers.get('Host', 'unknown')})")
            abort(403, description="Access denied. This service is only accessible through Cloudflare.")
    except Exception as e:
        logger.error(f"Error in Cloudflare protection check: {e}", exc_info=True)
        # On error, block request (fail closed) for security
        logger.warning("Cloudflare protection check failed, blocking request")
        abort(403, description="Access denied. Security check failed.")
    
    return None

