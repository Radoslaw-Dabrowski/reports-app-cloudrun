#!/bin/bash
# Setup Cloudflare Worker for existing reporting.dabronet.pl domain

set -e

# Configuration
CLOUDFLARE_API_TOKEN="${CLOUDFLARE_API_TOKEN:-}"
CLOUDFLARE_ACCOUNT_ID="${CLOUDFLARE_ACCOUNT_ID:-}"
DOMAIN="reporting.dabronet.pl"
CLOUD_RUN_URL="https://reports-app-cloudrun-299435740891.europe-west1.run.app"
WORKER_NAME="reports-app-proxy"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo "🚀 Setting up Cloudflare Worker for $DOMAIN..."

# Check required variables
if [ -z "$CLOUDFLARE_API_TOKEN" ]; then
    echo -e "${RED}❌ Error: CLOUDFLARE_API_TOKEN is required${NC}"
    exit 1
fi

if [ -z "$CLOUDFLARE_ACCOUNT_ID" ]; then
    echo -e "${RED}❌ Error: CLOUDFLARE_ACCOUNT_ID is required${NC}"
    exit 1
fi

# Get Zone ID
echo "🔍 Getting Zone ID for dabronet.pl..."
ZONE_ID=$(curl -s -X GET "https://api.cloudflare.com/client/v4/zones?name=dabronet.pl" \
    -H "Authorization: Bearer ${CLOUDFLARE_API_TOKEN}" \
    -H "Content-Type: application/json" | jq -r '.result[0].id')

if [ "$ZONE_ID" == "null" ] || [ -z "$ZONE_ID" ]; then
    echo -e "${RED}❌ Error: Domain dabronet.pl not found in Cloudflare${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Zone ID: $ZONE_ID${NC}"

# Create Worker
echo ""
echo "📦 Creating/Updating Worker: $WORKER_NAME..."

WORKER_CODE=$(cat <<EOF
addEventListener('fetch', event => {
  event.respondWith(handleRequest(event.request))
})

async function handleRequest(request) {
  const url = new URL(request.url);
  
  // Cloud Run service URL
  const cloudRunUrl = '${CLOUD_RUN_URL}' + url.pathname + url.search;
  
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

# Upload worker
UPLOAD_RESPONSE=$(curl -s -X PUT "https://api.cloudflare.com/client/v4/accounts/${CLOUDFLARE_ACCOUNT_ID}/workers/scripts/${WORKER_NAME}" \
    -H "Authorization: Bearer ${CLOUDFLARE_API_TOKEN}" \
    -H "Content-Type: application/javascript" \
    --data-binary "$WORKER_CODE")

if echo "$UPLOAD_RESPONSE" | jq -e '.success' > /dev/null; then
    echo -e "${GREEN}✅ Worker created/updated successfully${NC}"
else
    echo -e "${RED}❌ Error creating worker:${NC}"
    echo "$UPLOAD_RESPONSE" | jq '.errors'
    exit 1
fi

# Bind domain to worker
echo ""
echo "🔗 Binding $DOMAIN to worker..."

# First, try to get existing routes
EXISTING_ROUTES=$(curl -s -X GET "https://api.cloudflare.com/client/v4/zones/${ZONE_ID}/workers/routes" \
    -H "Authorization: Bearer ${CLOUDFLARE_API_TOKEN}" \
    -H "Content-Type: application/json")

# Check if route already exists
ROUTE_EXISTS=$(echo "$EXISTING_ROUTES" | jq -r ".result[] | select(.pattern == \"${DOMAIN}/*\") | .id")

if [ -n "$ROUTE_EXISTS" ] && [ "$ROUTE_EXISTS" != "null" ]; then
    echo "   Route exists, updating..."
    ROUTE_ID="$ROUTE_EXISTS"
    
    ROUTE_RESPONSE=$(curl -s -X PUT "https://api.cloudflare.com/client/v4/zones/${ZONE_ID}/workers/routes/${ROUTE_ID}" \
        -H "Authorization: Bearer ${CLOUDFLARE_API_TOKEN}" \
        -H "Content-Type: application/json" \
        -d "{
            \"pattern\": \"${DOMAIN}/*\",
            \"script\": \"${WORKER_NAME}\"
        }")
else
    echo "   Creating new route..."
    ROUTE_RESPONSE=$(curl -s -X POST "https://api.cloudflare.com/client/v4/zones/${ZONE_ID}/workers/routes" \
        -H "Authorization: Bearer ${CLOUDFLARE_API_TOKEN}" \
        -H "Content-Type: application/json" \
        -d "{
            \"pattern\": \"${DOMAIN}/*\",
            \"script\": \"${WORKER_NAME}\"
        }")
fi

if echo "$ROUTE_RESPONSE" | jq -e '.success' > /dev/null; then
    echo -e "${GREEN}✅ Domain bound successfully${NC}"
else
    echo -e "${YELLOW}⚠️  Warning: Could not bind domain. You may need to do it manually.${NC}"
    echo "$ROUTE_RESPONSE" | jq '.errors'
    echo ""
    echo "Manual steps:"
    echo "1. Go to Cloudflare Dashboard → Workers & Pages"
    echo "2. Click on worker: $WORKER_NAME"
    echo "3. Go to Settings → Triggers"
    echo "4. Add Custom Domain: $DOMAIN"
fi

echo ""
echo -e "${GREEN}✅ Setup complete!${NC}"
echo ""
echo "📋 Summary:"
echo "   Worker: $WORKER_NAME"
echo "   Domain: $DOMAIN"
echo "   Cloud Run: $CLOUD_RUN_URL"
echo ""
echo "🧪 Test:"
echo "   curl -I https://$DOMAIN"
echo ""
echo "ℹ️  Note: Cloudflare Access should already be configured for $DOMAIN"
echo "   If not, go to Zero Trust → Access → Applications and add it."

