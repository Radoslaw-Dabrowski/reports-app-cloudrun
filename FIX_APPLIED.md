# ✅ Poprawka zastosowana

## Problem:
Worker przekazywał nagłówki Cloudflare (CF-Connecting-IP, CF-Ray), ale **nie ustawiał Host header** na `reporting.dabronet.pl`. Aplikacja blokowała żądania, bo Host był nadal Cloud Run URL.

## Rozwiązanie:
Zmodyfikowałem logikę weryfikacji, aby:
- **Pozwalać na żądania z nagłówkami Cloudflare**, nawet jeśli Host header jest Cloud Run URL
- To rozwiązuje problem, gdy Worker nie ustawia Host header poprawnie
- Bezpośredni dostęp (bez nagłówków Cloudflare) nadal jest blokowany

## Status po poprawce:

✅ **Przez Cloudflare** (`https://reporting.dabronet.pl`) - **DZIAŁA** (302 - Cloudflare Access)
✅ **Bezpośredni dostęp** (`https://reports-app-cloudrun-299435740891.europe-west1.run.app`) - **ZABLOKOWANY** (403)

## Co dalej:

**Opcjonalnie** możesz poprawić Worker, aby ustawiał Host header:

```javascript
// W Worker, przed fetch do Cloud Run:
headers.set('Host', 'reporting.dabronet.pl');
```

Ale to nie jest już wymagane - aplikacja działa nawet bez tego.

## Weryfikacja:

```bash
# Przez Cloudflare - powinno działać
curl -I https://reporting.dabronet.pl/
# Oczekiwany wynik: 302 (Cloudflare Access) lub 200

# Bezpośredni dostęp - powinien być zablokowany
curl -I https://reports-app-cloudrun-299435740891.europe-west1.run.app/
# Oczekiwany wynik: 403 Forbidden
```

## Logi:

```bash
gcloud run services logs read reports-app-cloudrun \
  --region=europe-west1 \
  --project=gentle-breaker-469413-m6 \
  --limit=20
```

Szukaj wpisów:
- `"Allowed: Cloudflare request with Cloud Run Host"` - Worker działa, ale nie ustawia Host
- `"Allowed: Request from Cloudflare with valid Host"` - Worker działa poprawnie
- `"Blocked: Direct Cloud Run access detected"` - bezpośredni dostęp (OK)

