#!/bin/bash
# Setup Cloudflare Workers and Access via API

set -e

# Configuration
CLOUDFLARE_API_TOKEN="${CLOUDFLARE_API_TOKEN:-}"
CLOUDFLARE_ACCOUNT_ID="${CLOUDFLARE_ACCOUNT_ID:-}"
DOMAIN="${DOMAIN:-}"
SUBDOMAIN="${SUBDOMAIN:-reports}"
CLOUD_RUN_URL="https://reports-app-cloudrun-299435740891.europe-west1.run.app"
WORKER_NAME="reports-app-proxy"
ALLOWED_EMAIL_DOMAIN="${ALLOWED_EMAIL_DOMAIN:-}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "🚀 Setting up Cloudflare Workers and Access via API..."

# Check required variables
if [ -z "$CLOUDFLARE_API_TOKEN" ]; then
    echo -e "${RED}❌ Error: CLOUDFLARE_API_TOKEN is required${NC}"
    echo "Get your API token from: https://dash.cloudflare.com/profile/api-tokens"
    echo "Required permissions:"
    echo "  - Account: Cloudflare Workers:Edit"
    echo "  - Zone: Zone:Read, DNS:Edit"
    echo "  - Account: Access: Applications and Policies:Edit"
    exit 1
fi

if [ -z "$CLOUDFLARE_ACCOUNT_ID" ]; then
    echo -e "${RED}❌ Error: CLOUDFLARE_ACCOUNT_ID is required${NC}"
    echo "Get it from: https://dash.cloudflare.com -> Right sidebar -> Account ID"
    exit 1
fi

if [ -z "$DOMAIN" ]; then
    echo -e "${RED}❌ Error: DOMAIN is required${NC}"
    echo "Usage: DOMAIN=twoja-domena.com ./setup-cloudflare-api.sh"
    exit 1
fi

if [ -z "$ALLOWED_EMAIL_DOMAIN" ]; then
    echo -e "${YELLOW}⚠️  Warning: ALLOWED_EMAIL_DOMAIN not set. Access will allow all emails.${NC}"
    echo "Set ALLOWED_EMAIL_DOMAIN=@twoja-firma.com to restrict access"
fi

FULL_DOMAIN="${SUBDOMAIN}.${DOMAIN}"

echo "📋 Configuration:"
echo "   Domain: $DOMAIN"
echo "   Subdomain: $SUBDOMAIN"
echo "   Full domain: $FULL_DOMAIN"
echo "   Cloud Run URL: $CLOUD_RUN_URL"
echo "   Worker name: $WORKER_NAME"
echo ""

# Step 1: Get Zone ID
echo "🔍 Getting Zone ID for $DOMAIN..."
ZONE_ID=$(curl -s -X GET "https://api.cloudflare.com/client/v4/zones?name=${DOMAIN}" \
    -H "Authorization: Bearer ${CLOUDFLARE_API_TOKEN}" \
    -H "Content-Type: application/json" | jq -r '.result[0].id')

if [ "$ZONE_ID" == "null" ] || [ -z "$ZONE_ID" ]; then
    echo -e "${RED}❌ Error: Domain $DOMAIN not found in Cloudflare${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Zone ID: $ZONE_ID${NC}"

# Step 2: Create Worker
echo ""
echo "📦 Creating Worker: $WORKER_NAME..."

WORKER_CODE=$(cat <<'EOF'
addEventListener('fetch', event => {
  event.respondWith(handleRequest(event.request))
})

async function handleRequest(request) {
  const url = new URL(request.url);
  
  // Cloud Run service URL
  const cloudRunUrl = 'CLOUD_RUN_URL_PLACEHOLDER' + url.pathname + url.search;
  
  // Preserve original headers
  const headers = new Headers(request.headers);
  
  // Forward request to Cloud Run
  const modifiedRequest = new Request(cloudRunUrl, {
    method: request.method,
    headers: headers,
    body: request.body,
    redirect: 'follow'
  });
  
  try {
    const response = await fetch(modifiedRequest);
    
    // Return response with additional headers
    const newHeaders = new Headers(response.headers);
    newHeaders.set('X-Proxy', 'cloudflare-worker');
    
    return new Response(response.body, {
      status: response.status,
      statusText: response.statusText,
      headers: newHeaders
    });
  } catch (error) {
    return new Response('Proxy error: ' + error.message, { status: 502 });
  }
}
EOF
)

WORKER_CODE="${WORKER_CODE//CLOUD_RUN_URL_PLACEHOLDER/$CLOUD_RUN_URL}"

# Upload worker script
UPLOAD_RESPONSE=$(curl -s -X PUT "https://api.cloudflare.com/client/v4/accounts/${CLOUDFLARE_ACCOUNT_ID}/workers/scripts/${WORKER_NAME}" \
    -H "Authorization: Bearer ${CLOUDFLARE_API_TOKEN}" \
    -H "Content-Type: application/javascript" \
    --data-binary "$WORKER_CODE")

if echo "$UPLOAD_RESPONSE" | jq -e '.success' > /dev/null; then
    echo -e "${GREEN}✅ Worker created successfully${NC}"
else
    echo -e "${RED}❌ Error creating worker:${NC}"
    echo "$UPLOAD_RESPONSE" | jq '.errors'
    exit 1
fi

# Step 3: Bind custom domain to worker
echo ""
echo "🔗 Binding custom domain to worker..."

ROUTE_RESPONSE=$(curl -s -X PUT "https://api.cloudflare.com/client/v4/zones/${ZONE_ID}/workers/routes" \
    -H "Authorization: Bearer ${CLOUDFLARE_API_TOKEN}" \
    -H "Content-Type: application/json" \
    -d "{
        \"pattern\": \"${FULL_DOMAIN}/*\",
        \"script\": \"${WORKER_NAME}\"
    }")

if echo "$ROUTE_RESPONSE" | jq -e '.success' > /dev/null; then
    echo -e "${GREEN}✅ Custom domain bound successfully${NC}"
else
    # Try to update existing route
    echo "   Route might already exist, trying to update..."
    ROUTE_RESPONSE=$(curl -s -X PUT "https://api.cloudflare.com/client/v4/zones/${ZONE_ID}/workers/routes" \
        -H "Authorization: Bearer ${CLOUDFLARE_API_TOKEN}" \
        -H "Content-Type: application/json" \
        -d "{
            \"pattern\": \"${FULL_DOMAIN}/*\",
            \"script\": \"${WORKER_NAME}\"
        }")
    
    if echo "$ROUTE_RESPONSE" | jq -e '.success' > /dev/null; then
        echo -e "${GREEN}✅ Route updated successfully${NC}"
    else
        echo -e "${YELLOW}⚠️  Warning: Could not bind domain. You may need to do it manually.${NC}"
        echo "$ROUTE_RESPONSE" | jq '.errors'
    fi
fi

# Step 4: Create Cloudflare Access Application
echo ""
echo "🔐 Creating Cloudflare Access Application..."

# Create access application
ACCESS_APP_DATA=$(cat <<EOF
{
  "name": "Reports App",
  "domain": "${FULL_DOMAIN}",
  "type": "self_hosted",
  "session_duration": "24h",
  "policies": [
    {
      "name": "Authenticated Users",
      "decision": "allow",
      "include": [
        {
          "email_domain": {
            "domain": "${ALLOWED_EMAIL_DOMAIN}"
          }
        }
      ]
    }
  ]
}
EOF
)

# If no email domain specified, allow all authenticated users
if [ -z "$ALLOWED_EMAIL_DOMAIN" ]; then
    ACCESS_APP_DATA=$(cat <<EOF
{
  "name": "Reports App",
  "domain": "${FULL_DOMAIN}",
  "type": "self_hosted",
  "session_duration": "24h",
  "policies": [
    {
      "name": "Authenticated Users",
      "decision": "allow",
      "include": [
        {
          "email": {}
        }
      ]
    }
  ]
}
EOF
)
fi

ACCESS_APP_RESPONSE=$(curl -s -X POST "https://api.cloudflare.com/client/v4/accounts/${CLOUDFLARE_ACCOUNT_ID}/access/apps" \
    -H "Authorization: Bearer ${CLOUDFLARE_API_TOKEN}" \
    -H "Content-Type: application/json" \
    --data "$ACCESS_APP_DATA")

if echo "$ACCESS_APP_RESPONSE" | jq -e '.success' > /dev/null; then
    APP_ID=$(echo "$ACCESS_APP_RESPONSE" | jq -r '.result.id')
    echo -e "${GREEN}✅ Access Application created successfully (ID: $APP_ID)${NC}"
else
    echo -e "${YELLOW}⚠️  Warning: Could not create Access Application. You may need to do it manually.${NC}"
    echo "$ACCESS_APP_RESPONSE" | jq '.errors'
    echo ""
    echo "Manual steps:"
    echo "1. Go to Cloudflare Dashboard → Zero Trust → Access → Applications"
    echo "2. Add application for: $FULL_DOMAIN"
fi

# Step 5: Verify DNS (optional - Cloudflare should handle this automatically)
echo ""
echo "🔍 Verifying DNS configuration..."

DNS_RECORDS=$(curl -s -X GET "https://api.cloudflare.com/client/v4/zones/${ZONE_ID}/dns_records?name=${FULL_DOMAIN}" \
    -H "Authorization: Bearer ${CLOUDFLARE_API_TOKEN}" \
    -H "Content-Type: application/json")

if echo "$DNS_RECORDS" | jq -e '.result | length > 0' > /dev/null; then
    echo -e "${GREEN}✅ DNS record exists for $FULL_DOMAIN${NC}"
else
    echo -e "${YELLOW}⚠️  No DNS record found. Cloudflare Workers should handle routing automatically.${NC}"
fi

echo ""
echo -e "${GREEN}✅ Setup complete!${NC}"
echo ""
echo "📋 Summary:"
echo "   Worker: $WORKER_NAME"
echo "   Domain: $FULL_DOMAIN"
echo "   Cloud Run: $CLOUD_RUN_URL"
echo ""
echo "🧪 Test:"
echo "   curl -I https://$FULL_DOMAIN"
echo ""
echo "🔐 Access:"
echo "   Open https://$FULL_DOMAIN in browser"
echo "   You should see Cloudflare Access login page"

