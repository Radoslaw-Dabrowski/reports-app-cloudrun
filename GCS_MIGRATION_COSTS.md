# Koszty migracji danych z S3 do GCS

## Przegląd

Aplikacja została zmodyfikowana, aby używać Google Cloud Storage (GCS) jako cache dla danych z AWS S3. Dane są kopiowane z S3 do GCS po kliknięciu przycisku "Refresh Data", co redukuje koszty transferu danych z AWS.

## Jak to działa

1. **Źródło danych**: AWS S3 (bucket `dhc-reports`)
2. **Cache**: Google Cloud Storage (bucket `dhc-reports-cache`)
3. **Proces**:
   - Po kliknięciu "Refresh Data" → dane są kopiowane z S3 do GCS
   - Aplikacja czyta z GCS (jeśli dostępne), w przeciwnym razie z S3
   - Dane pozostają w S3 jako źródło prawdy

## Wyliczenie kosztów

### Założenia
- Rozmiar danych: **~1 GB** (szacunkowo, na podstawie 71652 wierszy w report.csv)
- Liczba plików CSV: **~20 plików**
- Odświeżania dziennie: **1x dziennie** (po kliknięciu "Refresh Data")
- Odczytów dziennie: **~100** (użytkownicy przeglądają raporty)

### Koszty jednorazowe (migracja)

#### AWS S3 Egress (transfer danych z S3 do GCS)
- **$0.09/GB** (pierwsze 10TB/miesiąc)
- Dla 1 GB: **$0.09**

#### GCS Write Operations (Class A)
- **$0.05/10,000 operacji**
- Dla 20 plików: **$0.0001** (20 / 10,000 * $0.05)

**Razem jednorazowo: ~$0.09**

### Koszty miesięczne (ongoing)

#### GCS Storage
- **$0.020/GB/miesiąc** (Standard Storage)
- Dla 1 GB: **$0.02/miesiąc**

#### GCS Read Operations (Class B)
- **$0.004/10,000 operacji**
- Dla 3000 odczytów/miesiąc (100/dzień * 30 dni): **$0.0012/miesiąc**

#### GCS Write Operations (Class A) - przy każdym refresh
- Dla 20 odświeżeń/miesiąc (1/dzień * 30 dni): **$0.0001/miesiąc**

**Razem miesięcznie: ~$0.021/miesiąc**

### Oszczędności vs. bezpośredni dostęp do S3

#### Bez GCS (tylko S3):
- AWS S3 Egress: **$0.09/GB** za każdy transfer
- Dla 3000 odczytów/miesiąc (każdy odczyt = 1 GB transferu): **$270/miesiąc** ❌

#### Z GCS (cache):
- Migracja jednorazowa: **$0.09**
- Koszty miesięczne: **$0.021/miesiąc** ✅

**Oszczędności: ~$270/miesiąc** (99.99% redukcja kosztów!)

## Konfiguracja

### Zmienne środowiskowe

```bash
# Google Cloud Storage (cache)
GCS_BUCKET_NAME=dhc-reports-cache
GCP_PROJECT_ID=gentle-breaker-469413-m6

# Źródło danych (preferencja: 'gcs' lub 's3')
DATA_SOURCE=gcs  # Aplikacja użyje GCS jeśli dostępne, w przeciwnym razie S3
```

### Utworzenie bucket GCS

```bash
# Utwórz bucket w GCS
gsutil mb -p gentle-breaker-469413-m6 -l europe-west1 gs://dhc-reports-cache

# Ustaw uprawnienia (Cloud Run service account)
gsutil iam ch serviceAccount:299435740891-compute@developer.gserviceaccount.com:roles/storage.objectAdmin gs://dhc-reports-cache
```

### Dodanie do Cloud Run

Dodaj zmienne środowiskowe do Cloud Run service:

```bash
gcloud run services update reports-app-cloudrun \
  --region=europe-west1 \
  --set-env-vars="GCS_BUCKET_NAME=dhc-reports-cache,GCP_PROJECT_ID=gentle-breaker-469413-m6,DATA_SOURCE=gcs"
```

## Użycie

1. **Pierwsze uruchomienie**: Kliknij "Refresh Data" w aplikacji
2. **Dane są kopiowane**: Z S3 do GCS (jednorazowy koszt ~$0.09)
3. **Aplikacja czyta z GCS**: Wszystkie kolejne odświeżenia używają GCS (bez kosztów AWS egress)
4. **Aktualizacja danych**: Kliknij "Refresh Data" ponownie, aby zsynchronizować z S3

## Monitoring kosztów

Endpoint `/refresh_cache` zwraca szczegółowe informacje o kosztach:

```json
{
  "status": "success",
  "message": "Copied 20 files (1.2 GB) from S3 to GCS",
  "total_size_gb": 1.2,
  "costs": {
    "one_time_migration": {
      "aws_egress_usd": 0.108,
      "gcs_write_ops_usd": 0.0001,
      "total_usd": 0.1081
    },
    "monthly_ongoing": {
      "gcs_storage_usd": 0.024,
      "gcs_read_ops_usd": 0.0012,
      "total_usd": 0.0252
    },
    "savings_vs_s3_egress": {
      "s3_egress_per_month_usd": 270.0,
      "gcs_total_per_month_usd": 0.0252,
      "savings_usd": 269.9748
    }
  }
}
```

## Uwagi

- **Dane źródłowe pozostają w S3**: GCS jest tylko cache'em
- **Automatyczny fallback**: Jeśli GCS jest pusty, aplikacja automatycznie używa S3
- **Synchronizacja**: Kliknij "Refresh Data", aby zsynchronizować dane z S3 do GCS
- **Koszty transferu GCS → Cloud Run**: **DARMOWE** (w tym samym regionie)

## Podsumowanie

| Metryka | Bez GCS | Z GCS | Oszczędności |
|---------|---------|-------|--------------|
| Koszt migracji | - | $0.09 | - |
| Koszt miesięczny | $270 | $0.02 | **$269.98** |
| Koszt roczny | $3,240 | $0.24 | **$3,239.76** |

**ROI: 99.99% redukcja kosztów transferu danych!**

