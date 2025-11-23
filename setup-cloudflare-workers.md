# Cloudflare Workers Setup (Rekomendowane)

## Dlaczego Workers zamiast Tunnel?

Cloud Run wymaga, aby kontener nasłuchiwał na porcie HTTP. Cloudflared tunnel nie nasłuchuje na porcie, więc nie działa dobrze z Cloud Run. Cloudflare Workers to lepsze rozwiązanie.

## Krok 1: Utwórz Worker

1. Zaloguj się do [Cloudflare Dashboard](https://dash.cloudflare.com)
2. Przejdź do **Workers & Pages**
3. Kliknij **Create application** → **Create Worker**
4. Nazwij: `reports-app-proxy`
5. Wklej kod:

```javascript
export default {
  async fetch(request, env) {
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
};
```

6. Kliknij **Deploy**

## Krok 2: Skonfiguruj Custom Domain

1. W Worker → **Settings** → **Triggers**
2. Kliknij **Add Custom Domain**
3. Wpisz: `reports.twoja-domena.com` (lub inny subdomain)
4. Cloudflare automatycznie skonfiguruje DNS

## Krok 3: Skonfiguruj Cloudflare Access

1. Cloudflare Dashboard → **Zero Trust** → **Access** → **Applications**
2. Kliknij **Add an application**
3. Wybierz **Self-hosted**
4. Skonfiguruj:
   - **Application name**: `Reports App`
   - **Application domain**: `reports.twoja-domena.com`
   - **Session duration**: `24 hours`
5. Kliknij **Next**
6. **Policy**:
   - **Policy name**: `Authenticated Users`
   - **Action**: `Allow`
   - **Include**: 
     - `Emails ending in` → `@twoja-firma.com`
     - Lub dodaj konkretne emaile
7. Kliknij **Add application**

## Krok 4: Weryfikacja

1. Otwórz `https://reports.twoja-domena.com` w przeglądarce
2. Powinieneś zobaczyć Cloudflare Access login page
3. Po zalogowaniu powinieneś mieć dostęp do aplikacji

## Zalety Workers

- ✅ Nie wymaga dodatkowego serwisu (jak cloudflared)
- ✅ Działa bezpośrednio z Cloud Run
- ✅ Szybsze (edge computing)
- ✅ Łatwiejsze w konfiguracji
- ✅ Darmowe dla rozsądnego użycia

## Troubleshooting

### Problem: 502 Bad Gateway

**Sprawdź:**
1. Czy Cloud Run service działa: `gcloud run services describe reports-app-cloudrun`
2. Czy URL w Worker jest poprawny
3. Czy Cloud Run akceptuje HTTPS

### Problem: Cloudflare Access nie działa

**Sprawdź:**
1. Czy aplikacja jest dodana w Cloudflare Access
2. Czy policy jest poprawnie skonfigurowana
3. Czy email jest w dozwolonych domenach

### Problem: CORS errors

Dodaj do Worker:

```javascript
// Add CORS headers
newHeaders.set('Access-Control-Allow-Origin', '*');
newHeaders.set('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, OPTIONS');
newHeaders.set('Access-Control-Allow-Headers', 'Content-Type, Authorization');
```

