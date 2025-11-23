# 🚀 Quick Deploy Guide - Reports App to Cloud Run

## Krok 1: Zainstaluj Google Cloud SDK

### macOS (Twój system)

```bash
# Opcja 1: Homebrew (recommended)
brew install --cask google-cloud-sdk

# Opcja 2: Installer
# Download from: https://cloud.google.com/sdk/docs/install
```

Po instalacji:
```bash
# Inicjalizuj gcloud
gcloud init

# Zaloguj się
gcloud auth login

# Wybierz lub stwórz projekt
gcloud projects create reports-app-prod --name="Reports App Production"

# Ustaw jako aktywny
gcloud config set project reports-app-prod
```

## Krok 2: Enable Required APIs

```bash
# Ustaw zmienną z project ID
export PROJECT_ID=$(gcloud config get-value project)

# Enable APIs (może zająć 2-3 minuty)
gcloud services enable \
    run.googleapis.com \
    cloudbuild.googleapis.com \
    secretmanager.googleapis.com \
    sqladmin.googleapis.com \
    redis.googleapis.com \
    vpcaccess.googleapis.com

echo "✅ APIs enabled!"
```

## Krok 3: Create Cloud SQL (PostgreSQL)

```bash
# Stwórz Cloud SQL instance (~5-10 minut)
gcloud sql instances create reports-db \
    --database-version=POSTGRES_14 \
    --tier=db-f1-micro \
    --region=europe-west1 \
    --root-password=$(openssl rand -base64 32)

# Zapisz hasło root (wyświetli się w output)

# Stwórz bazę danych
gcloud sql databases create reports_db \
    --instance=reports-db

# Stwórz użytkownika aplikacji
export DB_PASSWORD=$(openssl rand -base64 32)
echo "Database password: ${DB_PASSWORD}" > db_password.txt
echo "⚠️  Hasło zapisane w db_password.txt - ZACHOWAJ JE!"

gcloud sql users create reports_user \
    --instance=reports-db \
    --password=${DB_PASSWORD}

echo "✅ Cloud SQL created!"
```

## Krok 4: Create Cloud Memorystore (Redis)

```bash
# Stwórz Redis instance (~5 minut)
gcloud redis instances create reports-cache \
    --size=1 \
    --region=europe-west1 \
    --redis-version=redis_6_x

# Pobierz host Redis
export REDIS_HOST=$(gcloud redis instances describe reports-cache \
    --region=europe-west1 \
    --format='value(host)')

echo "Redis host: ${REDIS_HOST}"

echo "✅ Redis created!"
```

## Krok 5: Setup Secrets

```bash
# Przejdź do katalogu projektu
cd /Users/dabrowski/Documents/Projekty/reports-app-cloudrun

# Stwórz secrets
./scripts/setup-secrets.sh ${PROJECT_ID}

# Dodaj wartości secrets

# 1. Database credentials
echo -n "/cloudsql/${PROJECT_ID}:europe-west1:reports-db" | \
    gcloud secrets versions add reports-app-db-host --data-file=-

echo -n "reports_db" | \
    gcloud secrets versions add reports-app-db-name --data-file=-

echo -n "reports_user" | \
    gcloud secrets versions add reports-app-db-user --data-file=-

echo -n "${DB_PASSWORD}" | \
    gcloud secrets versions add reports-app-db-password --data-file=-

# 2. AWS S3 credentials (użyj swoich)
echo -n "YOUR_AWS_ACCESS_KEY" | \
    gcloud secrets versions add reports-app-aws-access-key --data-file=-

echo -n "YOUR_AWS_SECRET_KEY" | \
    gcloud secrets versions add reports-app-aws-secret-key --data-file=-

# 3. Redis host
echo -n "${REDIS_HOST}" | \
    gcloud secrets versions add reports-app-redis-host --data-file=-

# 4. Flask secret key
echo -n "$(openssl rand -hex 32)" | \
    gcloud secrets versions add reports-app-secret-key --data-file=-

echo "✅ Secrets configured!"
```

## Krok 6: Create Service Account

```bash
# Stwórz service account dla Cloud Run
gcloud iam service-accounts create reports-app-sa \
    --display-name="Reports App Service Account"

# Grant permissions
gcloud projects add-iam-policy-binding ${PROJECT_ID} \
    --member="serviceAccount:reports-app-sa@${PROJECT_ID}.iam.gserviceaccount.com" \
    --role="roles/cloudsql.client"

gcloud projects add-iam-policy-binding ${PROJECT_ID} \
    --member="serviceAccount:reports-app-sa@${PROJECT_ID}.iam.gserviceaccount.com" \
    --role="roles/secretmanager.secretAccessor"

echo "✅ Service account created!"
```

## Krok 7: Deploy to Cloud Run 🚀

```bash
# Build and deploy (to zajmie ~5-10 minut)
gcloud run deploy reports-app \
    --source . \
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
    --update-secrets="DB_HOST=reports-app-db-host:latest,DB_NAME=reports-app-db-name:latest,DB_USER=reports-app-db-user:latest,DB_PASSWORD=reports-app-db-password:latest,AWS_ACCESS_KEY_ID=reports-app-aws-access-key:latest,AWS_SECRET_ACCESS_KEY=reports-app-aws-secret-key:latest,REDIS_HOST=reports-app-redis-host:latest,SECRET_KEY=reports-app-secret-key:latest"

echo "✅ Deployed to Cloud Run!"
```

## Krok 8: Get Service URL

```bash
# Pobierz URL aplikacji
export SERVICE_URL=$(gcloud run services describe reports-app \
    --platform managed \
    --region europe-west1 \
    --format 'value(status.url)')

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🎉 DEPLOYMENT COMPLETE!"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "Service URL: ${SERVICE_URL}"
echo ""
echo "Test endpoints:"
echo "  Health check: curl ${SERVICE_URL}/health"
echo "  Readiness:    curl ${SERVICE_URL}/ready"
echo "  Home page:    open ${SERVICE_URL}"
echo ""
echo "Next steps:"
echo "1. Initialize database (create tables)"
echo "2. Load data from S3: curl -X POST ${SERVICE_URL}/refresh_cache"
echo "3. Open in browser: ${SERVICE_URL}"
echo ""
```

## Krok 9: Initialize Database

Będziesz musiał stworzyć tabele w bazie. Opcje:

### Opcja A: Manual SQL
```bash
# Connect to Cloud SQL
gcloud sql connect reports-db --user=reports_user --database=reports_db

# W psql prompt:
CREATE TABLE report (...);
CREATE TABLE frequencies (...);
-- etc.
```

### Opcja B: Migration script (TODO)
```bash
# Stwórz migration script który utworzy tabele
# python scripts/init_db.py
```

## 📊 Monitor Deployment

### View Logs
```bash
gcloud run services logs tail reports-app \
    --region=europe-west1 \
    --follow
```

### View Metrics
```bash
# Open Cloud Console
open "https://console.cloud.google.com/run/detail/europe-west1/reports-app/metrics?project=${PROJECT_ID}"
```

## 💰 Estimated Costs

**First month (free tier):**
- Cloud Run: Free tier covers ~2M requests
- Cloud SQL: ~$25/month (db-f1-micro)
- Redis: ~$10/month (M1)
- **Total: ~$35/month**

**Scale to zero = $0 when idle!** 🎉

## 🔧 Troubleshooting

### Build fails
```bash
# Check build logs
gcloud builds list --limit=1
gcloud builds log $(gcloud builds list --limit=1 --format='value(id)')
```

### Service not responding
```bash
# Check logs
gcloud run services logs read reports-app --region=europe-west1 --limit=100

# Check service status
gcloud run services describe reports-app --region=europe-west1
```

### Database connection errors
```bash
# Verify Cloud SQL instance is running
gcloud sql instances describe reports-db

# Check secrets
gcloud secrets versions access latest --secret=reports-app-db-password
```

## 🎯 One-Command Deploy (after initial setup)

Po pierwszym setupie, kolejne deploymenty:

```bash
gcloud run deploy reports-app \
    --source . \
    --region europe-west1
```

Gotowe! ✅

---

**Need help?** Check:
- Full docs: README.md
- Deployment guide: DEPLOYMENT.md
- Migration guide: MIGRATION.md
