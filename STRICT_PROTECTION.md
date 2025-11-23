# Strict Cloudflare Protection

Aplikacja teraz **wymaga** nagłówków Cloudflare (CF-Connecting-IP, CF-Ray, lub CF-IPCountry) dla wszystkich żądań oprócz `/health`.

## Co się zmieniło:

1. **Wymagane nagłówki Cloudflare** - bez nich żądanie jest blokowane, nawet jeśli Host header jest poprawny
2. **Blokada bezpośredniego dostępu** - wszystkie żądania do Cloud Run URL (`*.run.app`) są blokowane
3. **Fail-closed** - jeśli sprawdzanie ochrony się nie powiedzie, żądanie jest blokowane (dla bezpieczeństwa)

## Wymagania:

1. **Cloudflare Worker** musi przekazywać nagłówki Cloudflare do Cloud Run
2. **Worker** musi ustawiać Host header na `reporting.dabronet.pl`

## Aktualizacja Worker:

Zaktualizuj Worker w Cloudflare, aby przekazywał nagłówki:

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

## Wdrożenie zmian:

Po zaktualizowaniu Worker, zbuduj i wdróż nową wersję aplikacji:

```bash
cd /tmp/reports-app-cloudrun
./deploy-to-cloudrun.sh
```

Lub ręcznie:

```bash
cd /tmp/reports-app-cloudrun
gcloud builds submit --tag gcr.io/gentle-breaker-469413-m6/reports-app-cloudrun
gcloud run deploy reports-app-cloudrun \
  --image gcr.io/gentle-breaker-469413-m6/reports-app-cloudrun \
  --region europe-west1 \
  --project gentle-breaker-469413-m6
```

## Weryfikacja:

Po wdrożeniu:

1. **Przez Cloudflare** (`https://reporting.dabronet.pl`) - powinno działać ✅
2. **Bezpośrednio** (`https://reports-app-cloudrun-299435740891.europe-west1.run.app`) - powinno być zablokowane ❌ (403 Forbidden)

## Sprawdzenie logów:

```bash
gcloud run services logs read reports-app-cloudrun \
  --region=europe-west1 \
  --project=gentle-breaker-469413-m6 \
  --limit=20
```

Szukaj wpisów:
- `"Blocked: Valid Host but missing Cloudflare headers"` - Worker nie przekazuje nagłówków
- `"Blocked: Direct Cloud Run access detected"` - bezpośredni dostęp (OK)
- `"Allowed: Request from Cloudflare with valid Host"` - poprawny dostęp przez Cloudflare

