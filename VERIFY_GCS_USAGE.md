# Weryfikacja użycia GCS jako źródła danych

## Sprawdzenie konfiguracji

Aplikacja jest skonfigurowana do używania GCS jako źródła danych:

```bash
# Sprawdź zmienne środowiskowe
gcloud run services describe reports-app-cloudrun \
  --region=europe-west1 \
  --project=gentle-breaker-469413-m6 \
  --format="value(spec.template.spec.containers[0].env)"
```

Powinno pokazać:
- `DATA_SOURCE=gcs`
- `GCS_BUCKET_NAME=dhc-reports-cache`
- `GCP_PROJECT_ID=gentle-breaker-469413-m6`

## Sprawdzenie logów

W logach Cloud Run powinieneś widzieć:

**Gdy używa GCS:**
```
[INFO] Using GCS as data source (bucket: dhc-reports-cache)
[GCS] Reading report.csv from bucket dhc-reports-cache
```

**Gdy używa S3 (fallback):**
```
[WARNING] GCS cache empty, falling back to S3
[INFO] Using S3 as data source (bucket: dhc-reports)
[S3] Reading report.csv from bucket dhc-reports
```

## Endpoint debug

Możesz sprawdzić źródło danych przez endpoint:

```
https://reports-app-cloudrun-299435740891.europe-west1.run.app/debug/storage-info
```

Endpoint zwraca JSON z informacjami:
- `current_source`: "GCS" lub "S3"
- `current_bucket`: nazwa bucketu, z którego czytane są dane
- `gcs_available`: czy GCS jest dostępne
- `gcs_has_data`: czy GCS ma dane
- `key_files_status`: status kluczowych plików (report.csv, frequencies.csv, etc.)

## Sprawdzenie danych w GCS

```bash
# Lista plików w GCS
gsutil ls gs://dhc-reports-cache/

# Sprawdź konkretny plik
gsutil ls -lh gs://dhc-reports-cache/report.csv

# Sprawdź wszystkie pliki CSV
gsutil ls gs://dhc-reports-cache/*.csv
```

## Kopiowanie danych do GCS

Jeśli GCS jest pusty, kliknij "Refresh Data" w aplikacji. To skopiuje dane z S3 do GCS.

Alternatywnie, możesz sprawdzić endpoint:
```
https://reports-app-cloudrun-299435740891.europe-west1.run.app/refresh_cache?format=json
```

## Weryfikacja, że dane są z GCS

1. **Sprawdź logi** - powinny pokazywać `[GCS]` zamiast `[S3]`
2. **Sprawdź endpoint debug** - `current_source` powinno być "GCS"
3. **Sprawdź bucket GCS** - powinien zawierać pliki CSV

## Rozwiązywanie problemów

### Problem: Aplikacja używa S3 zamiast GCS

**Przyczyny:**
1. GCS bucket jest pusty - kliknij "Refresh Data"
2. `DATA_SOURCE` nie jest ustawione na `gcs`
3. Biblioteka `google-cloud-storage` nie jest zainstalowana

**Rozwiązanie:**
```bash
# 1. Sprawdź konfigurację
gcloud run services describe reports-app-cloudrun \
  --region=europe-west1 \
  --format="value(spec.template.spec.containers[0].env)" | grep DATA_SOURCE

# 2. Jeśli DATA_SOURCE nie jest 'gcs', ustaw:
gcloud run services update reports-app-cloudrun \
  --region=europe-west1 \
  --set-env-vars="DATA_SOURCE=gcs"

# 3. Skopiuj dane do GCS (kliknij "Refresh Data" w aplikacji)
```

### Problem: GCS bucket nie istnieje

```bash
# Utwórz bucket
gsutil mb -p gentle-breaker-469413-m6 -l europe-west1 gs://dhc-reports-cache

# Ustaw uprawnienia
gsutil iam ch serviceAccount:299435740891-compute@developer.gserviceaccount.com:roles/storage.objectAdmin gs://dhc-reports-cache
```

### Problem: Brak uprawnień do GCS

```bash
# Sprawdź uprawnienia
gsutil iam get gs://dhc-reports-cache

# Dodaj uprawnienia dla Cloud Run service account
gsutil iam ch serviceAccount:299435740891-compute@developer.gserviceaccount.com:roles/storage.objectAdmin gs://dhc-reports-cache
```

