# ✅ Ochrona Cloudflare wdrożona pomyślnie!

Nowa wersja aplikacji została wdrożona z **strict Cloudflare protection**.

## Status:

- ✅ **Bezpośredni dostęp** (`https://reports-app-cloudrun-299435740891.europe-west1.run.app`) - **ZABLOKOWANY** (403 Forbidden)
- ⚠️ **Przez Cloudflare** (`https://reporting.dabronet.pl`) - **Wymaga aktualizacji Worker**

## Co zostało wdrożone:

1. **Strict protection** - wymaga nagłówków Cloudflare (CF-Connecting-IP, CF-Ray, CF-IPCountry)
2. **Blokada bezpośredniego dostępu** - wszystkie żądania do Cloud Run URL są blokowane
3. **Fail-closed** - jeśli sprawdzanie się nie powiedzie, żądanie jest blokowane

## Następny krok - Aktualizacja Cloudflare Worker:

Worker **MUSI** przekazywać nagłówki Cloudflare. Zaktualizuj Worker w Cloudflare Dashboard:

1. Przejdź do [Cloudflare Dashboard](https://dash.cloudflare.com)
2. Workers & Pages → Twój Worker (np. `reports-app-proxy`)
3. Kliknij **Edit code**
4. Zastąp kod poniższym:

```javascript
addEventListener('fetch', event => {
  event.respondWith(handleRequest(event.request))
})

async function handleRequest(request) {
  const url = new URL(request.url);
  const cloudRunUrl = 'https://reports-app-cloudrun-299435740891.europe-west1.run.app' + url.pathname + url.search;
  
  // Create new headers - preserve Cloudflare headers
  const headers = new Headers();
  for (const [key, value] of request.headers) {
    headers.set(key, value);
  }
  headers.set('Host', 'reporting.dabronet.pl');
  
  const modifiedRequest = new Request(cloudRunUrl, {
    method: request.method,
    headers: headers,
    body: request.body,
    redirect: 'follow'
  });
  
  try {
    const response = await fetch(modifiedRequest);
    const newHeaders = new Headers(response.headers);
    newHeaders.set('X-Proxy', 'cloudflare-worker');
    return new Response(response.body, {
      status: response.status,
      statusText: response.statusText,
      headers: newHeaders
    });
  } catch (error) {
    return new Response('Proxy error: ' + error.message, { status: 502 });
  }
}
```

5. Kliknij **Save and deploy**

## Weryfikacja:

Po aktualizacji Worker:

```bash
# Bezpośredni dostęp - powinien być zablokowany
curl -I https://reports-app-cloudrun-299435740891.europe-west1.run.app/
# Oczekiwany wynik: 403 Forbidden

# Przez Cloudflare - powinien działać
curl -I https://reporting.dabronet.pl/
# Oczekiwany wynik: 200 OK (lub przekierowanie do Cloudflare Access)
```

## Sprawdzanie logów:

```bash
gcloud run services logs read reports-app-cloudrun \
  --region=europe-west1 \
  --project=gentle-breaker-469413-m6 \
  --limit=20
```

Szukaj wpisów:
- `"Blocked: Direct Cloud Run access detected"` - bezpośredni dostęp (OK)
- `"Blocked: Valid Host but missing Cloudflare headers"` - Worker nie przekazuje nagłówków
- `"Allowed: Request from Cloudflare with valid Host"` - poprawny dostęp przez Cloudflare

## Rozwiązywanie problemów:

Jeśli `reporting.dabronet.pl` nadal nie działa po aktualizacji Worker:

1. Sprawdź logi Cloud Run - czy są nagłówki Cloudflare?
2. Sprawdź logi Cloudflare Worker - czy Worker działa?
3. Sprawdź Cloudflare Access - czy nie blokuje żądań?

