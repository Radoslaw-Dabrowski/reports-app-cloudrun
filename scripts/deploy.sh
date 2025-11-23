#!/bin/bash
#
# Deployment script for Reports App to Google Cloud Run
# Usage: ./scripts/deploy.sh [PROJECT_ID] [REGION]
#

set -e

# Configuration
PROJECT_ID=${1:-"your-project-id"}
REGION=${2:-"europe-west1"}
SERVICE_NAME="reports-app"
IMAGE_NAME="gcr.io/${PROJECT_ID}/${SERVICE_NAME}"

echo "🚀 Deploying Reports App to Cloud Run"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Project: ${PROJECT_ID}"
echo "Region: ${REGION}"
echo "Service: ${SERVICE_NAME}"
echo ""

# Check if gcloud is installed
if ! command -v gcloud &> /dev/null; then
    echo "❌ Error: gcloud CLI is not installed"
    echo "Install from: https://cloud.google.com/sdk/docs/install"
    exit 1
fi

# Set project
echo "📝 Setting project..."
gcloud config set project ${PROJECT_ID}

# Build and push image
echo "🏗️  Building Docker image..."
gcloud builds submit --tag ${IMAGE_NAME}:latest

# Deploy to Cloud Run
echo "☁️  Deploying to Cloud Run..."
gcloud run deploy ${SERVICE_NAME} \
    --image ${IMAGE_NAME}:latest \
    --platform managed \
    --region ${REGION} \
    --allow-unauthenticated \
    --min-instances 0 \
    --max-instances 10 \
    --cpu 2 \
    --memory 2Gi \
    --timeout 300 \
    --concurrency 80 \
    --set-env-vars "FLASK_ENV=production,PORT=8080"

# Get service URL
SERVICE_URL=$(gcloud run services describe ${SERVICE_NAME} \
    --platform managed \
    --region ${REGION} \
    --format 'value(status.url)')

echo ""
echo "✅ Deployment complete!"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Service URL: ${SERVICE_URL}"
echo ""
echo "Next steps:"
echo "1. Configure secrets in Secret Manager"
echo "2. Set up Cloud SQL database"
echo "3. Configure Redis (Cloud Memorystore)"
echo "4. Test the application: curl ${SERVICE_URL}/health"
