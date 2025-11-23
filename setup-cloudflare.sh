#!/bin/bash
# Setup Cloudflare Tunnel for Cloud Run

set -e

PROJECT_ID="gentle-breaker-469413-m6"
REGION="europe-west1"
SERVICE_NAME="cloudflared-tunnel"
REPORTS_SERVICE="reports-app-cloudrun"
SECRET_NAME="cloudflared-token"

echo "🚀 Setting up Cloudflare Tunnel for Cloud Run..."

# Check if tunnel token is provided
if [ -z "$1" ]; then
    echo "❌ Error: Tunnel token required"
    echo "Usage: $0 <CLOUDFLARED_TUNNEL_TOKEN>"
    echo ""
    echo "To get tunnel token:"
    echo "1. Go to Cloudflare Dashboard → Zero Trust → Networks → Tunnels"
    echo "2. Create a new tunnel or use existing one"
    echo "3. Copy the tunnel token"
    exit 1
fi

TUNNEL_TOKEN="$1"

# Step 1: Create Secret Manager secret
echo "📦 Creating Secret Manager secret..."
if gcloud secrets describe "$SECRET_NAME" --project="$PROJECT_ID" &>/dev/null; then
    echo "   Secret already exists, updating..."
    echo -n "$TUNNEL_TOKEN" | gcloud secrets versions add "$SECRET_NAME" \
        --data-file=- \
        --project="$PROJECT_ID"
else
    echo -n "$TUNNEL_TOKEN" | gcloud secrets create "$SECRET_NAME" \
        --data-file=- \
        --project="$PROJECT_ID"
fi

# Grant Cloud Run service account access to secret
echo "🔐 Granting access to secret..."
gcloud secrets add-iam-policy-binding "$SECRET_NAME" \
    --member="serviceAccount:299435740891-compute@developer.gserviceaccount.com" \
    --role="roles/secretmanager.secretAccessor" \
    --project="$PROJECT_ID"

# Step 2: Deploy Cloud Run service for cloudflared
echo "🚀 Deploying Cloud Run service for cloudflared..."
gcloud run deploy "$SERVICE_NAME" \
    --image=cloudflare/cloudflared:latest \
    --region="$REGION" \
    --project="$PROJECT_ID" \
    --set-secrets="CLOUDFLARED_TOKEN=$SECRET_NAME:latest" \
    --args="tunnel,--no-autoupdate,run,--token,\$(CLOUDFLARED_TOKEN)" \
    --memory=256Mi \
    --cpu=1 \
    --min-instances=1 \
    --max-instances=2 \
    --timeout=3600 \
    --service-account=299435740891-compute@developer.gserviceaccount.com \
    --no-allow-unauthenticated \
    --port=8080 \
    --no-cpu-throttling \
    --execution-environment=gen2

echo ""
echo "✅ Cloudflare Tunnel service deployed!"
echo ""
echo "📋 Next steps:"
echo "1. Go to Cloudflare Dashboard → Zero Trust → Networks → Tunnels"
echo "2. Find your tunnel and go to 'Public Hostname'"
echo "3. Add a new route:"
echo "   - Subdomain: reports (or your choice)"
echo "   - Domain: your-domain.com"
echo "   - Service: https://$REPORTS_SERVICE-299435740891.$REGION.run.app"
echo ""
echo "4. Configure Cloudflare Access:"
echo "   - Go to Zero Trust → Access → Applications"
echo "   - Add application for your subdomain"
echo "   - Configure authentication policy"
echo ""
echo "5. Check tunnel logs:"
echo "   gcloud run services logs read $SERVICE_NAME --region=$REGION --limit=50"

