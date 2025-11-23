# Deployment Guide - Reports App Cloud Run

## Pre-deployment Checklist

### 1. Google Cloud Setup

```bash
# Install gcloud CLI
# https://cloud.google.com/sdk/docs/install

# Login to Google Cloud
gcloud auth login

# Set your project
export PROJECT_ID="your-project-id"
gcloud config set project ${PROJECT_ID}

# Enable required APIs
gcloud services enable run.googleapis.com
gcloud services enable cloudbuild.googleapis.com
gcloud services enable secretmanager.googleapis.com
gcloud services enable sqladmin.googleapis.com
gcloud services enable redis.googleapis.com
```

### 2. Create Cloud SQL Instance (PostgreSQL)

```bash
# Create instance
gcloud sql instances create reports-db \
    --database-version=POSTGRES_14 \
    --tier=db-f1-micro \
    --region=europe-west1 \
    --root-password=CHANGE_ME

# Create database
gcloud sql databases create reports_db \
    --instance=reports-db

# Create user
gcloud sql users create reports_user \
    --instance=reports-db \
    --password=CHANGE_ME
```

### 3. Create Cloud Memorystore (Redis)

```bash
gcloud redis instances create reports-cache \
    --size=1 \
    --region=europe-west1 \
    --redis-version=redis_6_x
```

### 4. Setup Secrets

```bash
# Run the setup script
./scripts/setup-secrets.sh ${PROJECT_ID}

# Add secret values
echo -n "your-db-host" | gcloud secrets versions add reports-app-db-host --data-file=-
echo -n "reports_db" | gcloud secrets versions add reports-app-db-name --data-file=-
echo -n "reports_user" | gcloud secrets versions add reports-app-db-user --data-file=-
echo -n "your-db-password" | gcloud secrets versions add reports-app-db-password --data-file=-
echo -n "your-aws-key" | gcloud secrets versions add reports-app-aws-access-key --data-file=-
echo -n "your-aws-secret" | gcloud secrets versions add reports-app-aws-secret-key --data-file=-
echo -n "10.0.0.3" | gcloud secrets versions add reports-app-redis-host --data-file=-
echo -n "$(openssl rand -hex 32)" | gcloud secrets versions add reports-app-secret-key --data-file=-
```

### 5. Create Service Account

```bash
# Create service account
gcloud iam service-accounts create reports-app-sa \
    --display-name="Reports App Service Account"

# Grant permissions
gcloud projects add-iam-policy-binding ${PROJECT_ID} \
    --member="serviceAccount:reports-app-sa@${PROJECT_ID}.iam.gserviceaccount.com" \
    --role="roles/cloudsql.client"

gcloud projects add-iam-policy-binding ${PROJECT_ID} \
    --member="serviceAccount:reports-app-sa@${PROJECT_ID}.iam.gserviceaccount.com" \
    --role="roles/secretmanager.secretAccessor"
```

## Deployment

### Option 1: Using deployment script

```bash
./scripts/deploy.sh ${PROJECT_ID} europe-west1
```

### Option 2: Manual deployment

```bash
# Build image
gcloud builds submit --tag gcr.io/${PROJECT_ID}/reports-app:latest

# Deploy to Cloud Run
gcloud run deploy reports-app \
    --image gcr.io/${PROJECT_ID}/reports-app:latest \
    --platform managed \
    --region europe-west1 \
    --service-account reports-app-sa@${PROJECT_ID}.iam.gserviceaccount.com \
    --allow-unauthenticated \
    --min-instances 0 \
    --max-instances 10 \
    --cpu 2 \
    --memory 2Gi \
    --timeout 300 \
    --concurrency 80 \
    --add-cloudsql-instances ${PROJECT_ID}:europe-west1:reports-db \
    --set-secrets="DB_HOST=reports-app-db-host:latest,DB_NAME=reports-app-db-name:latest,DB_USER=reports-app-db-user:latest,DB_PASSWORD=reports-app-db-password:latest,AWS_ACCESS_KEY_ID=reports-app-aws-access-key:latest,AWS_SECRET_ACCESS_KEY=reports-app-aws-secret-key:latest,REDIS_HOST=reports-app-redis-host:latest,SECRET_KEY=reports-app-secret-key:latest"
```

## Post-deployment

### 1. Test the service

```bash
# Get service URL
SERVICE_URL=$(gcloud run services describe reports-app \
    --platform managed \
    --region europe-west1 \
    --format 'value(status.url)')

# Test health endpoint
curl ${SERVICE_URL}/health

# Test readiness endpoint
curl ${SERVICE_URL}/ready

# Open in browser
open ${SERVICE_URL}
```

### 2. Initialize database

```bash
# Connect to Cloud SQL and run migrations
gcloud sql connect reports-db --user=reports_user

# In psql prompt, create tables as needed
```

### 3. Load initial data

```bash
# Trigger S3 sync
curl -X POST ${SERVICE_URL}/refresh_cache
```

## Monitoring

### View logs

```bash
gcloud run services logs tail reports-app \
    --region=europe-west1 \
    --follow
```

### View metrics

Open Cloud Console:
https://console.cloud.google.com/run/detail/europe-west1/reports-app/metrics

## Updating the application

```bash
# Make changes to code
git add .
git commit -m "Update: description"
git push

# Redeploy
./scripts/deploy.sh ${PROJECT_ID} europe-west1
```

## Rollback

```bash
# List revisions
gcloud run revisions list --service=reports-app --region=europe-west1

# Rollback to previous revision
gcloud run services update-traffic reports-app \
    --region=europe-west1 \
    --to-revisions=REVISION_NAME=100
```

## Troubleshooting

### Cold start too slow

```bash
# Set minimum instances to 1 (costs more)
gcloud run services update reports-app \
    --region=europe-west1 \
    --min-instances=1
```

### Out of memory

```bash
# Increase memory
gcloud run services update reports-app \
    --region=europe-west1 \
    --memory=4Gi
```

### Connection timeout

```bash
# Increase timeout
gcloud run services update reports-app \
    --region=europe-west1 \
    --timeout=600
```
