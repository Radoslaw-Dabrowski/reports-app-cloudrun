#!/bin/bash
#
# Complete setup and deployment script for Reports App on Cloud Run
# This script will:
# 1. Check prerequisites
# 2. Create GCP resources (Cloud SQL, Redis)
# 3. Setup secrets
# 4. Deploy to Cloud Run
#
# Usage: ./scripts/full-setup.sh [PROJECT_ID]
#

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
PROJECT_ID=${1:-""}
REGION="europe-west1"
SERVICE_NAME="reports-app"
DB_INSTANCE="reports-db"
REDIS_INSTANCE="reports-cache"

echo -e "${BLUE}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  Reports App - Cloud Run Complete Setup"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo -e "${NC}"

# Check if gcloud is installed
if ! command -v gcloud &> /dev/null; then
    echo -e "${RED}❌ Error: gcloud CLI is not installed${NC}"
    echo ""
    echo "Install it from: https://cloud.google.com/sdk/docs/install"
    echo ""
    echo "For macOS:"
    echo "  brew install --cask google-cloud-sdk"
    echo ""
    exit 1
fi

# Check if project ID is provided
if [ -z "$PROJECT_ID" ]; then
    echo -e "${YELLOW}No project ID provided. Using current project...${NC}"
    PROJECT_ID=$(gcloud config get-value project 2>/dev/null)
    
    if [ -z "$PROJECT_ID" ]; then
        echo -e "${RED}❌ No active GCP project found${NC}"
        echo ""
        echo "Please run:"
        echo "  gcloud init"
        echo ""
        echo "Or provide project ID:"
        echo "  ./scripts/full-setup.sh YOUR_PROJECT_ID"
        exit 1
    fi
fi

echo -e "${GREEN}✓ Using project: ${PROJECT_ID}${NC}"
gcloud config set project ${PROJECT_ID}

# Confirm with user
echo ""
echo -e "${YELLOW}This script will:${NC}"
echo "  1. Enable required GCP APIs"
echo "  2. Create Cloud SQL instance (PostgreSQL) - ~10 min"
echo "  3. Create Cloud Memorystore (Redis) - ~5 min"
echo "  4. Setup secrets in Secret Manager"
echo "  5. Create service account"
echo "  6. Deploy application to Cloud Run - ~5 min"
echo ""
echo -e "${YELLOW}Total estimated time: ~20-30 minutes${NC}"
echo -e "${YELLOW}Estimated cost: ~$35/month${NC}"
echo ""
read -p "Continue? (y/n) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Aborted."
    exit 0
fi

# Step 1: Enable APIs
echo ""
echo -e "${BLUE}━━━ Step 1/6: Enabling APIs ━━━${NC}"
echo "Enabling required APIs (this may take a few minutes)..."

gcloud services enable \
    run.googleapis.com \
    cloudbuild.googleapis.com \
    secretmanager.googleapis.com \
    sqladmin.googleapis.com \
    redis.googleapis.com \
    vpcaccess.googleapis.com \
    --quiet

echo -e "${GREEN}✓ APIs enabled${NC}"

# Step 2: Create Cloud SQL
echo ""
echo -e "${BLUE}━━━ Step 2/6: Creating Cloud SQL ━━━${NC}"

# Check if instance already exists
if gcloud sql instances describe ${DB_INSTANCE} --quiet 2>/dev/null; then
    echo -e "${YELLOW}⚠ Cloud SQL instance ${DB_INSTANCE} already exists, skipping...${NC}"
else
    echo "Creating Cloud SQL instance (this will take ~10 minutes)..."
    
    DB_ROOT_PASSWORD=$(openssl rand -base64 32)
    
    gcloud sql instances create ${DB_INSTANCE} \
        --database-version=POSTGRES_14 \
        --tier=db-f1-micro \
        --region=${REGION} \
        --root-password="${DB_ROOT_PASSWORD}" \
        --quiet
    
    echo "Root password: ${DB_ROOT_PASSWORD}" > .db_root_password.txt
    echo -e "${YELLOW}⚠ Root password saved to .db_root_password.txt${NC}"
    
    # Create database
    gcloud sql databases create reports_db \
        --instance=${DB_INSTANCE} \
        --quiet
    
    # Create user
    DB_PASSWORD=$(openssl rand -base64 32)
    gcloud sql users create reports_user \
        --instance=${DB_INSTANCE} \
        --password="${DB_PASSWORD}" \
        --quiet
    
    echo "${DB_PASSWORD}" > .db_password.txt
    echo -e "${YELLOW}⚠ User password saved to .db_password.txt${NC}"
    
    echo -e "${GREEN}✓ Cloud SQL created${NC}"
fi

# Step 3: Create Redis
echo ""
echo -e "${BLUE}━━━ Step 3/6: Creating Redis ━━━${NC}"

# Check if instance already exists
if gcloud redis instances describe ${REDIS_INSTANCE} --region=${REGION} --quiet 2>/dev/null; then
    echo -e "${YELLOW}⚠ Redis instance ${REDIS_INSTANCE} already exists, skipping...${NC}"
else
    echo "Creating Redis instance (this will take ~5 minutes)..."
    
    gcloud redis instances create ${REDIS_INSTANCE} \
        --size=1 \
        --region=${REGION} \
        --redis-version=redis_6_x \
        --quiet
    
    echo -e "${GREEN}✓ Redis created${NC}"
fi

# Get Redis host
REDIS_HOST=$(gcloud redis instances describe ${REDIS_INSTANCE} \
    --region=${REGION} \
    --format='value(host)')
echo "Redis host: ${REDIS_HOST}"

# Step 4: Setup Secrets
echo ""
echo -e "${BLUE}━━━ Step 4/6: Setting up secrets ━━━${NC}"

# Create secrets if they don't exist
for secret in reports-app-db-host reports-app-db-name reports-app-db-user \
              reports-app-db-password reports-app-redis-host reports-app-secret-key; do
    if ! gcloud secrets describe ${secret} --quiet 2>/dev/null; then
        gcloud secrets create ${secret} --replication-policy="automatic" --quiet
    fi
done

# Add secret values
echo "Adding secret values..."

echo -n "/cloudsql/${PROJECT_ID}:${REGION}:${DB_INSTANCE}" | \
    gcloud secrets versions add reports-app-db-host --data-file=- --quiet

echo -n "reports_db" | \
    gcloud secrets versions add reports-app-db-name --data-file=- --quiet

echo -n "reports_user" | \
    gcloud secrets versions add reports-app-db-user --data-file=- --quiet

if [ -f .db_password.txt ]; then
    cat .db_password.txt | \
        gcloud secrets versions add reports-app-db-password --data-file=- --quiet
fi

echo -n "${REDIS_HOST}" | \
    gcloud secrets versions add reports-app-redis-host --data-file=- --quiet

echo -n "$(openssl rand -hex 32)" | \
    gcloud secrets versions add reports-app-secret-key --data-file=- --quiet

echo -e "${YELLOW}⚠ AWS credentials need to be set manually:${NC}"
echo "  echo -n 'YOUR_KEY' | gcloud secrets versions add reports-app-aws-access-key --data-file=-"
echo "  echo -n 'YOUR_SECRET' | gcloud secrets versions add reports-app-aws-secret-key --data-file=-"

echo -e "${GREEN}✓ Secrets configured${NC}"

# Step 5: Create Service Account
echo ""
echo -e "${BLUE}━━━ Step 5/6: Creating service account ━━━${NC}"

SA_EMAIL="reports-app-sa@${PROJECT_ID}.iam.gserviceaccount.com"

# Check if service account exists
if gcloud iam service-accounts describe ${SA_EMAIL} --quiet 2>/dev/null; then
    echo -e "${YELLOW}⚠ Service account already exists, skipping...${NC}"
else
    gcloud iam service-accounts create reports-app-sa \
        --display-name="Reports App Service Account" \
        --quiet
fi

# Grant roles
gcloud projects add-iam-policy-binding ${PROJECT_ID} \
    --member="serviceAccount:${SA_EMAIL}" \
    --role="roles/cloudsql.client" \
    --quiet 2>/dev/null || true

gcloud projects add-iam-policy-binding ${PROJECT_ID} \
    --member="serviceAccount:${SA_EMAIL}" \
    --role="roles/secretmanager.secretAccessor" \
    --quiet 2>/dev/null || true

echo -e "${GREEN}✓ Service account configured${NC}"

# Step 6: Deploy to Cloud Run
echo ""
echo -e "${BLUE}━━━ Step 6/6: Deploying to Cloud Run ━━━${NC}"
echo "Building and deploying (this will take ~5-10 minutes)..."

gcloud run deploy ${SERVICE_NAME} \
    --source . \
    --platform managed \
    --region ${REGION} \
    --service-account ${SA_EMAIL} \
    --allow-unauthenticated \
    --min-instances 0 \
    --max-instances 10 \
    --cpu 2 \
    --memory 2Gi \
    --timeout 300 \
    --concurrency 80 \
    --add-cloudsql-instances ${PROJECT_ID}:${REGION}:${DB_INSTANCE} \
    --update-secrets="DB_HOST=reports-app-db-host:latest,DB_NAME=reports-app-db-name:latest,DB_USER=reports-app-db-user:latest,DB_PASSWORD=reports-app-db-password:latest,REDIS_HOST=reports-app-redis-host:latest,SECRET_KEY=reports-app-secret-key:latest" \
    --quiet

# Get service URL
SERVICE_URL=$(gcloud run services describe ${SERVICE_NAME} \
    --platform managed \
    --region ${REGION} \
    --format 'value(status.url)')

echo ""
echo -e "${GREEN}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  🎉 DEPLOYMENT COMPLETE!"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo -e "${NC}"
echo ""
echo -e "${BLUE}Service URL:${NC} ${SERVICE_URL}"
echo ""
echo -e "${BLUE}Test endpoints:${NC}"
echo "  Health check: curl ${SERVICE_URL}/health"
echo "  Readiness:    curl ${SERVICE_URL}/ready"
echo "  Home page:    open ${SERVICE_URL}"
echo ""
echo -e "${YELLOW}⚠ Next steps:${NC}"
echo "  1. Set AWS credentials in Secret Manager (see above)"
echo "  2. Initialize database tables"
echo "  3. Load data: curl -X POST ${SERVICE_URL}/refresh_cache"
echo ""
echo -e "${BLUE}Monitor:${NC}"
echo "  Logs:    gcloud run services logs tail ${SERVICE_NAME} --region=${REGION}"
echo "  Metrics: https://console.cloud.google.com/run/detail/${REGION}/${SERVICE_NAME}/metrics?project=${PROJECT_ID}"
echo ""
echo -e "${GREEN}Setup complete! 🚀${NC}"
