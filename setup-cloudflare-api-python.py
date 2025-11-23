#!/usr/bin/env python3
"""
Setup Cloudflare Workers and Access via API (Python version)
"""
import os
import sys
import json
import requests
from typing import Optional, Dict, Any

# Configuration
CLOUDFLARE_API_TOKEN = os.getenv('CLOUDFLARE_API_TOKEN')
CLOUDFLARE_ACCOUNT_ID = os.getenv('CLOUDFLARE_ACCOUNT_ID')
DOMAIN = os.getenv('DOMAIN')
SUBDOMAIN = os.getenv('SUBDOMAIN', 'reports')
CLOUD_RUN_URL = "https://reports-app-cloudrun-299435740891.europe-west1.run.app"
WORKER_NAME = "reports-app-proxy"
ALLOWED_EMAIL_DOMAIN = os.getenv('ALLOWED_EMAIL_DOMAIN')

BASE_URL = "https://api.cloudflare.com/client/v4"

def check_requirements():
    """Check if all required environment variables are set"""
    if not CLOUDFLARE_API_TOKEN:
        print("❌ Error: CLOUDFLARE_API_TOKEN is required")
        print("Get your API token from: https://dash.cloudflare.com/profile/api-tokens")
        sys.exit(1)
    
    if not CLOUDFLARE_ACCOUNT_ID:
        print("❌ Error: CLOUDFLARE_ACCOUNT_ID is required")
        print("Get it from: https://dash.cloudflare.com -> Right sidebar -> Account ID")
        sys.exit(1)
    
    if not DOMAIN:
        print("❌ Error: DOMAIN is required")
        print("Usage: DOMAIN=twoja-domena.com python3 setup-cloudflare-api-python.py")
        sys.exit(1)

def make_request(method: str, endpoint: str, data: Optional[Dict] = None) -> Dict[str, Any]:
    """Make API request to Cloudflare"""
    url = f"{BASE_URL}{endpoint}"
    headers = {
        "Authorization": f"Bearer {CLOUDFLARE_API_TOKEN}",
        "Content-Type": "application/json"
    }
    
    if method == "GET":
        response = requests.get(url, headers=headers)
    elif method == "POST":
        response = requests.post(url, headers=headers, json=data)
    elif method == "PUT":
        response = requests.put(url, headers=headers, json=data)
    elif method == "DELETE":
        response = requests.delete(url, headers=headers)
    else:
        raise ValueError(f"Unsupported method: {method}")
    
    response.raise_for_status()
    return response.json()

def get_zone_id(domain: str) -> str:
    """Get Zone ID for domain"""
    print(f"🔍 Getting Zone ID for {domain}...")
    response = make_request("GET", f"/zones?name={domain}")
    
    if not response.get('result') or len(response['result']) == 0:
        print(f"❌ Error: Domain {domain} not found in Cloudflare")
        sys.exit(1)
    
    zone_id = response['result'][0]['id']
    print(f"✅ Zone ID: {zone_id}")
    return zone_id

def create_worker(account_id: str, worker_name: str, cloud_run_url: str) -> bool:
    """Create or update Cloudflare Worker"""
    print(f"📦 Creating Worker: {worker_name}...")
    
    # Get allowed host (use first from ALLOWED_HOSTS or domain)
    allowed_host = ALLOWED_EMAIL_DOMAIN if ALLOWED_EMAIL_DOMAIN and not ALLOWED_EMAIL_DOMAIN.startswith('@') else DOMAIN
    if SUBDOMAIN:
        allowed_host = f"{SUBDOMAIN}.{DOMAIN}"
    
    worker_code = f"""addEventListener('fetch', event => {{
  event.respondWith(handleRequest(event.request))
}})

async function handleRequest(request) {{
  const url = new URL(request.url);
  
  // Cloud Run service URL
  const cloudRunUrl = '{cloud_run_url}' + url.pathname + url.search;
  
  // Create new headers - preserve Cloudflare headers and add Host
  const headers = new Headers();
  
  // Copy all original headers (including Cloudflare headers like CF-Connecting-IP, CF-Ray)
  for (const [key, value] of request.headers) {{
    headers.set(key, value);
  }}
  
  // Ensure Host header is set to the original domain (for Cloud Run protection)
  headers.set('Host', '{allowed_host}');
  
  // Forward request to Cloud Run
  const modifiedRequest = new Request(cloudRunUrl, {{
    method: request.method,
    headers: headers,
    body: request.body,
    redirect: 'follow'
  }});
  
  try {{
    const response = await fetch(modifiedRequest);
    
    // Return response with additional headers
    const newHeaders = new Headers(response.headers);
    newHeaders.set('X-Proxy', 'cloudflare-worker');
    
    return new Response(response.body, {{
      status: response.status,
      statusText: response.statusText,
      headers: newHeaders
    }});
  }} catch (error) {{
    return new Response('Proxy error: ' + error.message, {{ status: 502 }});
  }}
}}"""
    
    # Upload worker script (using PUT for create/update)
    url = f"{BASE_URL}/accounts/{account_id}/workers/scripts/{worker_name}"
    headers = {
        "Authorization": f"Bearer {CLOUDFLARE_API_TOKEN}",
        "Content-Type": "application/javascript"
    }
    
    try:
        response = requests.put(url, headers=headers, data=worker_code)
        response.raise_for_status()
        print("✅ Worker created successfully")
        return True
    except requests.exceptions.HTTPError as e:
        print(f"❌ Error creating worker: {e}")
        if response.text:
            print(response.text)
        return False

def bind_worker_route(zone_id: str, domain: str, worker_name: str) -> bool:
    """Bind custom domain to worker"""
    print(f"🔗 Binding custom domain to worker...")
    
    data = {
        "pattern": f"{domain}/*",
        "script": worker_name
    }
    
    try:
        response = make_request("PUT", f"/zones/{zone_id}/workers/routes", data)
        if response.get('success'):
            print("✅ Custom domain bound successfully")
            return True
        else:
            print("⚠️  Warning: Could not bind domain")
            print(json.dumps(response.get('errors', []), indent=2))
            return False
    except Exception as e:
        print(f"⚠️  Warning: Could not bind domain: {e}")
        return False

def create_access_application(account_id: str, domain: str, email_domain: Optional[str] = None) -> Optional[str]:
    """Create Cloudflare Access Application"""
    print("🔐 Creating Cloudflare Access Application...")
    
    if email_domain:
        policy_include = [{"email_domain": {"domain": email_domain}}]
    else:
        policy_include = [{"email": {}}]
    
    data = {
        "name": "Reports App",
        "domain": domain,
        "type": "self_hosted",
        "session_duration": "24h",
        "policies": [
            {
                "name": "Authenticated Users",
                "decision": "allow",
                "include": policy_include
            }
        ]
    }
    
    try:
        response = make_request("POST", f"/accounts/{account_id}/access/apps", data)
        if response.get('success'):
            app_id = response['result']['id']
            print(f"✅ Access Application created successfully (ID: {app_id})")
            return app_id
        else:
            print("⚠️  Warning: Could not create Access Application")
            print(json.dumps(response.get('errors', []), indent=2))
            return None
    except Exception as e:
        print(f"⚠️  Warning: Could not create Access Application: {e}")
        return None

def main():
    """Main function"""
    print("🚀 Setting up Cloudflare Workers and Access via API...\n")
    
    check_requirements()
    
    full_domain = f"{SUBDOMAIN}.{DOMAIN}"
    
    print("📋 Configuration:")
    print(f"   Domain: {DOMAIN}")
    print(f"   Subdomain: {SUBDOMAIN}")
    print(f"   Full domain: {full_domain}")
    print(f"   Cloud Run URL: {CLOUD_RUN_URL}")
    print(f"   Worker name: {WORKER_NAME}")
    if ALLOWED_EMAIL_DOMAIN:
        print(f"   Allowed email domain: {ALLOWED_EMAIL_DOMAIN}")
    else:
        print("   ⚠️  Allowed email domain: All (not restricted)")
    print()
    
    # Get Zone ID
    zone_id = get_zone_id(DOMAIN)
    print()
    
    # Create Worker
    if create_worker(CLOUDFLARE_ACCOUNT_ID, WORKER_NAME, CLOUD_RUN_URL):
        print()
        
        # Bind route
        bind_worker_route(zone_id, full_domain, WORKER_NAME)
        print()
        
        # Create Access Application
        app_id = create_access_application(CLOUDFLARE_ACCOUNT_ID, full_domain, ALLOWED_EMAIL_DOMAIN)
        print()
        
        print("✅ Setup complete!\n")
        print("📋 Summary:")
        print(f"   Worker: {WORKER_NAME}")
        print(f"   Domain: {full_domain}")
        print(f"   Cloud Run: {CLOUD_RUN_URL}")
        if app_id:
            print(f"   Access App ID: {app_id}")
        print()
        print("🧪 Test:")
        print(f"   curl -I https://{full_domain}")
        print()
        print("🔐 Access:")
        print(f"   Open https://{full_domain} in browser")
        print("   You should see Cloudflare Access login page")
    else:
        print("❌ Failed to create worker. Please check errors above.")
        sys.exit(1)

if __name__ == "__main__":
    main()

