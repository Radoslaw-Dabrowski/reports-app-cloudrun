# 🚀 START HERE - Deploy to Cloud Run

## ✅ Kod jest już na GitHub!
https://github.com/Radoslaw-Dabrowski/reports-app-cloudrun

## Teraz: Deploy na Google Cloud Run

### KROK 1: Zainstaluj Google Cloud SDK

**macOS** (Twój system):
```bash
# Zainstaluj przez Homebrew
brew install --cask google-cloud-sdk

# Lub pobierz installer:
# https://cloud.google.com/sdk/docs/install
```

**Po instalacji:**
```bash
# Dodaj gcloud do PATH (jeśli potrzeba)
echo 'source "$(brew --prefix)/share/google-cloud-sdk/path.bash.inc"' >> ~/.zshrc
echo 'source "$(brew --prefix)/share/google-cloud-sdk/completion.bash.inc"' >> ~/.zshrc
source ~/.zshrc

# Sprawdź czy działa
gcloud --version
```

### KROK 2: Inicjalizuj GCP

```bash
# Zaloguj się
gcloud auth login

# Zainicjalizuj (wybierz lub stwórz projekt)
gcloud init

# Lub stwórz nowy projekt:
gcloud projects create reports-app-prod --name="Reports App Production"
gcloud config set project reports-app-prod

# Enable billing (WYMAGANE!)
# https://console.cloud.google.com/billing/linkedaccount?project=reports-app-prod
```

### KROK 3: Setup AWS Credentials

Potrzebujesz credentials do AWS S3 (dla bucket: dhc-reports)

Stwórz plik z credentials:
```bash
cd /Users/dabrowski/Documents/Projekty/reports-app-cloudrun

# Edytuj ten plik i dodaj swoje credentials:
cat > .aws_credentials << 'EOF'
AWS_ACCESS_KEY_ID=TWOJ_ACCESS_KEY
AWS_SECRET_ACCESS_KEY=TWOJ_SECRET_KEY
EOF
```

### KROK 4: RUN AUTOMATED SETUP! 🚀

```bash
cd /Users/dabrowski/Documents/Projekty/reports-app-cloudrun

# To zrobi WSZYSTKO automatycznie:
# - Enable APIs
# - Create Cloud SQL
# - Create Redis
# - Setup secrets
# - Deploy to Cloud Run
./scripts/full-setup.sh

# Potrwa ~20-30 minut (większość to czekanie na GCP resources)
```

Skrypt zapyta Cię o potwierdzenie przed rozpoczęciem.

### KROK 5: Dodaj AWS Credentials

Po deployment, dodaj AWS credentials do Secret Manager:

```bash
# Pobierz z .aws_credentials
source .aws_credentials

echo -n "${AWS_ACCESS_KEY_ID}" | \
    gcloud secrets versions add reports-app-aws-access-key --data-file=-

echo -n "${AWS_SECRET_ACCESS_KEY}" | \
    gcloud secrets versions add reports-app-aws-secret-key --data-file=-

# Redeploy aby załadować nowe secrets
gcloud run deploy reports-app --source . --region europe-west1
```

### KROK 6: Test!

```bash
# Pobierz URL aplikacji
SERVICE_URL=$(gcloud run services describe reports-app \
    --region=europe-west1 --format='value(status.url)')

# Test health check
curl ${SERVICE_URL}/health

# Open in browser
open ${SERVICE_URL}

# Załaduj dane z S3
curl -X POST ${SERVICE_URL}/refresh_cache
```

## 🎉 GOTOWE!

Aplikacja działa na Cloud Run i:
- ✅ Skaluje się automatycznie (0-10 instancji)
- ✅ Kosztuje $0 gdy idle (scale to zero!)
- ✅ Używa Cloud SQL dla danych
- ✅ Używa Redis dla cache
- ✅ Łączy się z AWS S3 dla raportów

---

## 💰 Koszty

**Miesięcznie (szacunkowo):**
- Cloud Run: $0-10 (zależy od ruchu)
- Cloud SQL: ~$25 (db-f1-micro)
- Redis: ~$10 (M1 instance)
- **Total: ~$35-45/month**

**Scale to zero = $0 podczas idle!** 🎯

---

## 📚 Dokumentacja

- **QUICK_DEPLOY.md** - Step-by-step manual setup
- **DEPLOYMENT.md** - Detailed deployment guide
- **MIGRATION.md** - K8s vs Cloud Run comparison
- **README.md** - Full documentation

---

## 🆘 Pomoc?

Jeśli coś nie działa:

1. **Check logs:**
   ```bash
   gcloud run services logs tail reports-app --region=europe-west1
   ```

2. **Check build:**
   ```bash
   gcloud builds list --limit=5
   ```

3. **Verify resources:**
   ```bash
   gcloud sql instances list
   gcloud redis instances list --region=europe-west1
   ```

4. **Check GitHub repo:**
   https://github.com/Radoslaw-Dabrowski/reports-app-cloudrun

---

## ⚡ Quick Commands

```bash
# Redeploy (after code changes)
gcloud run deploy reports-app --source . --region europe-west1

# View logs
gcloud run services logs tail reports-app --region=europe-west1 --follow

# Get service URL
gcloud run services describe reports-app --region=europe-west1 --format='value(status.url)'

# Delete everything (cleanup)
gcloud run services delete reports-app --region=europe-west1
gcloud sql instances delete reports-db
gcloud redis instances delete reports-cache --region=europe-west1
```
