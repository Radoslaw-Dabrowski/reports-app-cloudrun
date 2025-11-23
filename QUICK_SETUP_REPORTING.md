# Szybka konfiguracja reporting.dabronet.pl → Cloud Run

## Masz już:
- ✅ Cloudflare Access skonfigurowane dla `reporting.dabronet.pl`
- ✅ Policy w Access

## Co trzeba zrobić:

### Opcja 1: Automatycznie (przez API)

```bash
export CLOUDFLARE_API_TOKEN="twoj-token"
export CLOUDFLARE_ACCOUNT_ID="twoj-account-id"

./setup-reporting-domain.sh
```

### Opcja 2: Ręcznie (przez Dashboard)

#### Krok 1: Utwórz Cloudflare Worker

1. Cloudflare Dashboard → **Workers & Pages** → **Create application** → **Create Worker**
2. Nazwij: `reports-app-proxy`
3. Wklej kod:

```javascript
addEventListener('fetch', event => {
  event.respondWith(handleRequest(event.request))
})

async function handleRequest(request) {
  const url = new URL(request.url);
  
  // Cloud Run service URL
  const cloudRunUrl = 'https://reports-app-cloudrun-299435740891.europe-west1.run.app' + url.pathname + url.search;
  
  // Preserve original headers
  const headers = new Headers(request.headers);
  
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

4. Kliknij **Deploy**

#### Krok 2: Skonfiguruj Custom Domain

1. W Worker → **Settings** → **Triggers**
2. Kliknij **Add Custom Domain**
3. Wpisz: `reporting.dabronet.pl`
4. Cloudflare automatycznie skonfiguruje DNS

#### Krok 3: Sprawdź Cloudflare Access

1. Cloudflare Dashboard → **Zero Trust** → **Access** → **Applications**
2. Znajdź aplikację dla `reporting.dabronet.pl`
3. Upewnij się, że:
   - **Application domain**: `reporting.dabronet.pl`
   - **Policy** jest skonfigurowana

## Weryfikacja

Po skonfigurowaniu:

```bash
# Sprawdź dostępność
curl -I https://reporting.dabronet.pl

# Powinno zwrócić nagłówki z Cloud Run
```

Otwórz w przeglądarce:
- `https://reporting.dabronet.pl`
- Powinieneś zobaczyć Cloudflare Access login (jeśli skonfigurowane)
- Po zalogowaniu → aplikacja Cloud Run

## Troubleshooting

### Problem: 502 Bad Gateway

**Sprawdź:**
1. Czy Cloud Run service działa:
   ```bash
   gcloud run services describe reports-app-cloudrun --region=europe-west1
   ```
2. Czy URL w Worker jest poprawny
3. Czy Cloud Run akceptuje HTTPS

### Problem: Cloudflare Access nie działa

**Sprawdź:**
1. Czy aplikacja jest dodana w Access dla `reporting.dabronet.pl`
2. Czy policy jest poprawnie skonfigurowana
3. Czy email jest w dozwolonych

### Problem: Worker nie działa

**Sprawdź:**
1. Czy Worker jest deployed
2. Czy custom domain jest dodany
3. Czy DNS wskazuje na Cloudflare

## Podsumowanie

1. ✅ Utwórz Worker z kodem proxy
2. ✅ Dodaj custom domain `reporting.dabronet.pl` do workera
3. ✅ Sprawdź, że Cloudflare Access jest skonfigurowane
4. ✅ Przetestuj dostęp

Po tym `reporting.dabronet.pl` będzie wskazywać na Cloud Run przez Cloudflare Worker z autentykacją Access.

