# Wymuszenie użycia tylko GCS (bez S3)

## Konfiguracja

Aby wymusić użycie TYLKO GCS i zablokować S3, ustaw zmienne środowiskowe:

```bash
# Opcja 1: Użyj DATA_SOURCE=gcs-only (blokuje S3 jeśli GCS nie jest dostępne)
gcloud run services update reports-app-cloudrun \
  --region=europe-west1 \
  --set-env-vars="DATA_SOURCE=gcs-only"

# Opcja 2: Użyj FORCE_GCS_ONLY=true (najbardziej restrykcyjne)
gcloud run services update reports-app-cloudrun \
  --region=europe-west1 \
  --set-env-vars="FORCE_GCS_ONLY=true"
```

## Różnice między opcjami

### `DATA_SOURCE=gcs-only`
- Wymusza użycie GCS
- Jeśli GCS nie jest dostępne lub pusty → **błąd aplikacji**
- Nie pozwala na fallback do S3

### `FORCE_GCS_ONLY=true`
- Najbardziej restrykcyjne
- Wymusza użycie GCS
- Jeśli GCS nie jest dostępne → **błąd aplikacji**
- Jeśli GCS jest pusty → **błąd aplikacji**
- Kompletnie blokuje użycie S3

## Weryfikacja

### 1. Sprawdź endpoint debug

```
https://reports-app-cloudrun-299435740891.europe-west1.run.app/debug/storage-info
```

Powinno pokazać:
```json
{
  "current_source": "GCS",
  "force_gcs_only": true,
  "s3_used": false,
  "s3_blocked": true,
  "status": "GCS_ONLY"
}
```

### 2. Sprawdź logi

```bash
gcloud run services logs read reports-app-cloudrun \
  --region=europe-west1 \
  --limit=100 | grep -E "\[S3\]|Using S3|FORCED|GCS-only"
```

**Nie powinno być żadnych logów z `[S3]` lub `Using S3`.**

Powinno być:
```
[FORCED] Using GCS as data source (bucket: dhc-reports-cache)
[GCS] Reading report.csv from bucket dhc-reports-cache
```

### 3. Sprawdź, czy S3 jest używany

```bash
# Sprawdź logi pod kątem wywołań S3
gcloud run services logs read reports-app-cloudrun \
  --region=europe-west1 \
  --limit=200 | grep -i "s3\|aws" | grep -v "GCS"
```

**Powinno być puste** (brak wywołań do S3).

## Przed włączeniem GCS-only

1. **Upewnij się, że GCS ma dane:**
   ```bash
   gsutil ls gs://dhc-reports-cache/*.csv
   ```

2. **Jeśli GCS jest pusty, skopiuj dane:**
   - Kliknij "Refresh Data" w aplikacji
   - Lub użyj endpointu `/refresh_cache`

3. **Sprawdź uprawnienia:**
   ```bash
   gsutil iam get gs://dhc-reports-cache | grep "299435740891-compute@developer.gserviceaccount.com"
   ```

## Rozwiązywanie problemów

### Błąd: "FORCE_GCS_ONLY is enabled but GCS is not available"

**Przyczyna:** Biblioteka `google-cloud-storage` nie jest zainstalowana.

**Rozwiązanie:**
- Poczekaj na zakończenie builda (biblioteka jest w requirements.txt)
- Lub zainstaluj ręcznie w Dockerfile

### Błąd: "GCS bucket is empty"

**Przyczyna:** GCS bucket nie ma danych.

**Rozwiązanie:**
1. Tymczasowo wyłącz `FORCE_GCS_ONLY`:
   ```bash
   gcloud run services update reports-app-cloudrun \
     --region=europe-west1 \
     --set-env-vars="FORCE_GCS_ONLY=false"
   ```

2. Kliknij "Refresh Data" w aplikacji

3. Włącz ponownie `FORCE_GCS_ONLY`:
   ```bash
   gcloud run services update reports-app-cloudrun \
     --region=europe-west1 \
     --set-env-vars="FORCE_GCS_ONLY=true"
   ```

### Sprawdzenie, czy S3 jest używany

Użyj endpointu debug:
```bash
curl https://reports-app-cloudrun-299435740891.europe-west1.run.app/debug/storage-info | jq '.s3_used'
```

Powinno zwrócić `false`.

## Monitorowanie

### Alert, jeśli S3 jest używany

Możesz dodać alert w Cloud Monitoring:

```bash
# Sprawdź logi pod kątem użycia S3
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=reports-app-cloudrun AND textPayload=~\"Using S3\"" \
  --limit=1 \
  --format=json
```

Jeśli zwraca wyniki → S3 jest używany (nie powinno być).

## Podsumowanie

Aby wymusić użycie TYLKO GCS:

1. ✅ Ustaw `FORCE_GCS_ONLY=true` lub `DATA_SOURCE=gcs-only`
2. ✅ Upewnij się, że GCS ma dane (kliknij "Refresh Data")
3. ✅ Sprawdź endpoint `/debug/storage-info` - `s3_used` powinno być `false`
4. ✅ Sprawdź logi - nie powinno być `[S3]` ani `Using S3`

