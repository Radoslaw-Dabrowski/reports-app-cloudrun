# Aktualizacja Cloudflare Worker

Worker musi przekazywać nagłówki Cloudflare i ustawiać poprawny Host header.

## Szybka aktualizacja przez Cloudflare Dashboard

1. Zaloguj się do [Cloudflare Dashboard](https://dash.cloudflare.com)
2. Wybierz domenę `dabronet.pl`
3. Przejdź do **Workers & Pages** → **reports-worker** (lub nazwa Twojego workera)
4. Kliknij **Edit code**
5. Zastąp kod workera poniższym:

```javascript
addEventListener('fetch', event => {
  event.respondWith(handleRequest(event.request))
})

async function handleRequest(request) {
  const url = new URL(request.url);
  
  // Cloud Run service URL
  const cloudRunUrl = 'https://reports-app-cloudrun-299435740891.europe-west1.run.app' + url.pathname + url.search;
  
  // Create new headers - preserve Cloudflare headers and add Host
  const headers = new Headers();
  
  // Copy all original headers (including Cloudflare headers like CF-Connecting-IP, CF-Ray)
  for (const [key, value] of request.headers) {
    headers.set(key, value);
  }
  
  // Ensure Host header is set to the original domain (for Cloud Run protection)
  headers.set('Host', 'reporting.dabronet.pl');
  
  // Forward request to Cloud Run
  const modifiedRequest = new Request(cloudRunUrl, {
    method: request.method,
    headers: headers,
    body: request.body,
    redirect: 'follow'
  });
  
  try {
    const response = await fetch(modifiedRequest);
    
    // Return response with additional headers
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

6. Kliknij **Save and deploy**

## Automatyczna aktualizacja przez API

Użyj skryptu:

```bash
cd /tmp/reports-app-cloudrun
./setup-reporting-domain.sh
```

Lub ręcznie przez API:

```bash
export CLOUDFLARE_API_TOKEN="your-token"
export CLOUDFLARE_ACCOUNT_ID="your-account-id"
export WORKER_NAME="reports-worker"
export CLOUD_RUN_URL="https://reports-app-cloudrun-299435740891.europe-west1.run.app"
export DOMAIN="reporting.dabronet.pl"

# Zaktualizuj Worker
curl -X PUT "https://api.cloudflare.com/client/v4/accounts/${CLOUDFLARE_ACCOUNT_ID}/workers/scripts/${WORKER_NAME}" \
  -H "Authorization: Bearer ${CLOUDFLARE_API_TOKEN}" \
  -H "Content-Type: application/javascript" \
  --data-binary @- <<'EOF'
addEventListener('fetch', event => {
  event.respondWith(handleRequest(event.request))
})

async function handleRequest(request) {
  const url = new URL(request.url);
  const cloudRunUrl = 'https://reports-app-cloudrun-299435740891.europe-west1.run.app' + url.pathname + url.search;
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
EOF
```

## Weryfikacja

Po aktualizacji sprawdź:

1. **Przez Cloudflare** (`https://reporting.dabronet.pl`) - powinno działać ✅
2. **Bezpośrednio** (`https://reports-app-cloudrun-299435740891.europe-west1.run.app`) - powinno być zablokowane ❌

Jeśli nadal nie działa, sprawdź logi Cloud Run:

```bash
gcloud run services logs read reports-app-cloudrun --region=europe-west1 --project=gentle-breaker-469413-m6 --limit=20
```

