# Zabezpieczenie Cloud Run przed bezpośrednim dostępem

## Przegląd

Aplikacja została zabezpieczona, aby akceptować tylko żądania z Cloudflare (przez `reporting.dabronet.pl`). Bezpośredni dostęp do Cloud Run URL jest zablokowany.

## Jak to działa

Aplikacja sprawdza:
1. **Nagłówki Cloudflare** - `CF-Connecting-IP` lub `CF-Ray` (dodawane przez Cloudflare)
2. **Host header** - musi być `reporting.dabronet.pl`
3. **IP ranges** - opcjonalnie sprawdza, czy IP jest w zakresach Cloudflare

Jeśli żądanie nie przejdzie weryfikacji → **403 Forbidden**

## Konfiguracja

### Zmienne środowiskowe

```bash
# Wymagaj Cloudflare (domyślnie: true)
REQUIRE_CLOUDFLARE=true

# Dozwolone hosty (domyślnie: reporting.dabronet.pl)
ALLOWED_HOSTS=reporting.dabronet.pl

# Wyłącz ochronę (tylko dla testów)
REQUIRE_CLOUDFLARE=false
```

### Ustawienie w Cloud Run

```bash
gcloud run services update reports-app-cloudrun \
  --region=europe-west1 \
  --set-env-vars="REQUIRE_CLOUDFLARE=true,ALLOWED_HOSTS=reporting.dabronet.pl"
```

## Testowanie

### ✅ Powinno działać:

```bash
# Przez Cloudflare
curl -H "Host: reporting.dabronet.pl" \
     -H "CF-Connecting-IP: 1.2.3.4" \
     https://reports-app-cloudrun-299435740891.europe-west1.run.app/
```

### ❌ Powinno być zablokowane:

```bash
# Bezpośredni dostęp (bez nagłówków Cloudflare)
curl https://reports-app-cloudrun-299435740891.europe-west1.run.app/

# Złym Host header
curl -H "Host: evil.com" \
     https://reports-app-cloudrun-299435740891.europe-west1.run.app/
```

## Wyjątki

Następujące endpointy są zawsze dostępne (dla health checks):
- `/health` - health check
- `/ready` - readiness check

## Logi

W logach Cloud Run zobaczysz:

**Zablokowane żądanie:**
```
[WARNING] Blocked direct access attempt from 1.2.3.4 (Host: reports-app-cloudrun-299435740891.europe-west1.run.app)
[WARNING] Blocked unauthorized access: GET / from 1.2.3.4
```

**Dozwolone żądanie:**
```
[INFO] Request from Cloudflare (CF-Connecting-IP: 1.2.3.4, Host: reporting.dabronet.pl)
```

## Wyłączenie ochrony (tylko dla testów)

```bash
gcloud run services update reports-app-cloudrun \
  --region=europe-west1 \
  --set-env-vars="REQUIRE_CLOUDFLARE=false"
```

## Bezpieczeństwo

### Co jest chronione:
- ✅ Wszystkie endpointy (oprócz `/health` i `/ready`)
- ✅ Sprawdzanie nagłówków Cloudflare
- ✅ Sprawdzanie Host header
- ✅ Opcjonalne sprawdzanie IP ranges

### Co NIE jest chronione:
- Health checks (`/health`, `/ready`) - muszą być dostępne dla Cloud Run
- Jeśli `REQUIRE_CLOUDFLARE=false` - ochrona jest wyłączona

## Troubleshooting

### Problem: Nie mogę dostać się przez reporting.dabronet.pl

**Sprawdź:**
1. Czy Cloudflare Worker jest skonfigurowany
2. Czy Worker przekazuje nagłówki Cloudflare
3. Czy `ALLOWED_HOSTS` zawiera `reporting.dabronet.pl`

### Problem: Health checks nie działają

**Rozwiązanie:** Health checks (`/health`, `/ready`) są zawsze dostępne, niezależnie od ochrony.

### Problem: Chcę tymczasowo wyłączyć ochronę

```bash
gcloud run services update reports-app-cloudrun \
  --region=europe-west1 \
  --set-env-vars="REQUIRE_CLOUDFLARE=false"
```

## Podsumowanie

Po wdrożeniu:
- ✅ Bezpośredni dostęp do Cloud Run URL → **403 Forbidden**
- ✅ Dostęp przez `reporting.dabronet.pl` → **Działa** (z autentykacją Cloudflare Access)
- ✅ Health checks → **Zawsze dostępne**

Aplikacja jest teraz dostępna TYLKO przez Cloudflare!

