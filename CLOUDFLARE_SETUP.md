# Konfiguracja Cloudflare dla Cloud Run

## Przegląd

Aby zabezpieczyć Cloud Run i dodać autentykację przez Cloudflare, potrzebujemy:
1. **Cloudflare Tunnel** - bezpieczne połączenie między Cloudflare a Cloud Run
2. **Cloudflare Access** - autentykacja użytkowników przed dostępem
3. **Ograniczenie dostępu** - Cloud Run akceptuje tylko ruch z Cloudflare

## Opcja 1: Cloudflare Tunnel (Rekomendowane)

### Krok 1: Utwórz Tunnel w Cloudflare

1. Zaloguj się do Cloudflare Dashboard
2. Przejdź do **Zero Trust** → **Networks** → **Tunnels**
3. Kliknij **Create a tunnel**
4. Wybierz **Cloudflared** (lub **Cloud Run** jeśli dostępne)
5. Nazwij tunnel: `reports-app-cloudrun`
6. Skopiuj **Tunnel Token**

### Krok 2: Utwórz Cloud Run service dla Cloudflared

**UWAGA:** Cloudflared tunnel nie nasłuchuje na porcie HTTP, więc Cloud Run może zgłaszać błędy. Użyj przygotowanego skryptu lub alternatywnego rozwiązania.

**Opcja A: Użyj przygotowanego skryptu (zalecane)**

```bash
cd /tmp/reports-app-cloudrun
./setup-cloudflare.sh YOUR_TUNNEL_TOKEN
```

**Opcja B: Alternatywne rozwiązanie - Cloudflare Workers**

Jeśli Cloud Run nie działa z cloudflared, użyj Cloudflare Workers jako proxy (patrz Opcja 2 poniżej).

**Opcja C: Uruchom cloudflared lokalnie lub na innym serwerze**

Cloudflared może działać na dowolnym serwerze, nie musi być w Cloud Run. Możesz:
- Uruchomić na swoim serwerze domowym
- Użyć Cloud Run Jobs (zamiast Service)
- Użyć Compute Engine VM

### Krok 3: Skonfiguruj Route w Cloudflare

1. W Cloudflare Dashboard → **Zero Trust** → **Networks** → **Tunnels**
2. Kliknij na swój tunnel
3. Przejdź do **Public Hostname**
4. Dodaj nowy hostname:
   - **Subdomain**: `reports` (lub inny)
   - **Domain**: Twoja domena (np. `twoja-domena.com`)
   - **Service**: `https://reports-app-cloudrun-299435740891.europe-west1.run.app`
   - **Path**: (zostaw puste)

### Krok 4: Skonfiguruj Cloudflare Access

1. W Cloudflare Dashboard → **Zero Trust** → **Access** → **Applications**
2. Kliknij **Add an application**
3. Wybierz **Self-hosted**
4. Skonfiguruj:
   - **Application name**: `Reports App`
   - **Application domain**: `reports.twoja-domena.com` (lub inny subdomain)
   - **Session duration**: `24 hours` (lub inny)
5. Kliknij **Next**
6. **Policy**:
   - **Policy name**: `Authenticated Users`
   - **Action**: `Allow`
   - **Include**: 
     - `Emails` → Dodaj dozwolone emaile (np. `@twoja-firma.com`)
     - Lub `Emails ending in` → `@twoja-firma.com`
7. Kliknij **Add application**

## Opcja 2: Cloudflare Workers (Rekomendowane dla Cloud Run)

Cloudflare Workers to lepsze rozwiązanie dla Cloud Run, ponieważ nie wymaga dodatkowego serwisu.

### Krok 1: Utwórz Worker

1. Zaloguj się do Cloudflare Dashboard
2. Przejdź do **Workers & Pages**
3. Kliknij **Create application** → **Create Worker**
4. Nazwij: `reports-app-proxy`
5. Wklej kod:

```javascript
// worker.js
addEventListener('fetch', event => {
  event.respondWith(handleRequest(event.request))
})

async function handleRequest(request) {
  const url = new URL(request.url);
  
  // Cloud Run service URL
  const cloudRunUrl = 'https://reports-app-cloudrun-299435740891.europe-west1.run.app' + url.pathname + url.search;
  
  // Create new request with original headers
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
    
    // Create new response with CORS headers if needed
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

6. Kliknij **Deploy**

### Krok 2: Skonfiguruj Route

1. W Worker → **Triggers**
2. Dodaj **Custom Domain** lub użyj ***.workers.dev**
3. Ustaw domenę: `reports.twoja-domena.com`

### Krok 3: Skonfiguruj Cloudflare Access

1. Cloudflare Dashboard → **Zero Trust** → **Access** → **Applications**
2. **Add an application** → **Self-hosted**
3. Skonfiguruj:
   - **Application name**: `Reports App`
   - **Application domain**: `reports.twoja-domena.com`
   - **Policy**: Dodaj dozwolone emaile

## Opcja 3: Cloudflare Tunnel (Alternatywa - jeśli Workers nie działa)

Jeśli nie chcesz używać Tunnel, możesz użyć Cloudflare Workers jako proxy:

### Krok 1: Utwórz Worker

```javascript
// worker.js
addEventListener('fetch', event => {
  event.respondWith(handleRequest(event.request))
})

async function handleRequest(request) {
  const url = new URL(request.url)
  
  // Forward request to Cloud Run
  const cloudRunUrl = 'https://reports-app-cloudrun-299435740891.europe-west1.run.app' + url.pathname + url.search
  
  const modifiedRequest = new Request(cloudRunUrl, {
    method: request.method,
    headers: request.headers,
    body: request.body
  })
  
  const response = await fetch(modifiedRequest)
  
  // Return response
  return new Response(response.body, {
    status: response.status,
    statusText: response.statusText,
    headers: response.headers
  })
}
```

### Krok 2: Wdróż Worker

```bash
# Zainstaluj Wrangler
npm install -g wrangler

# Zaloguj się
wrangler login

# Wdróż worker
wrangler publish
```

## Opcja 3: Ograniczenie dostępu tylko do Cloudflare IP

### Krok 1: Pobierz Cloudflare IP ranges

```bash
# Pobierz IPv4 ranges
curl https://www.cloudflare.com/ips-v4 > cloudflare-ips-v4.txt

# Pobierz IPv6 ranges
curl https://www.cloudflare.com/ips-v6 > cloudflare-ips-v6.txt
```

### Krok 2: Skonfiguruj Cloud Armor (jeśli używasz Load Balancer)

Alternatywnie, możesz użyć Cloud Run z VPC connector i skonfigurować Cloud Armor.

## Konfiguracja Cloud Run dla Cloudflare

### Ograniczenie nagłówków

Cloud Run powinien akceptować nagłówki Cloudflare. Dodaj do aplikacji:

```python
# app/__init__.py
@app.before_request
def check_cloudflare():
    """Verify request comes from Cloudflare (optional)"""
    # Cloudflare dodaje nagłówek CF-Connecting-IP
    # Możesz sprawdzić, czy request pochodzi z Cloudflare
    cf_ip = request.headers.get('CF-Connecting-IP')
    if cf_ip:
        # Request pochodzi z Cloudflare
        pass
    # Możesz też sprawdzić CF-Ray header
    cf_ray = request.headers.get('CF-Ray')
```

### Konfiguracja CORS (jeśli potrzebne)

```python
from flask_cors import CORS

# W app/__init__.py
CORS(app, origins=[
    "https://reports.twoja-domena.com",
    "https://*.twoja-domena.com"
])
```

## Weryfikacja

### 1. Sprawdź, czy tunnel działa

```bash
# Sprawdź logi cloudflared-tunnel
gcloud run services logs read cloudflared-tunnel \
  --region=europe-west1 \
  --limit=50
```

### 2. Sprawdź dostępność przez Cloudflare

```bash
# Sprawdź przez Cloudflare domain
curl -I https://reports.twoja-domena.com

# Powinno zwrócić Cloudflare nagłówki
```

### 3. Sprawdź autentykację

1. Otwórz `https://reports.twoja-domena.com` w przeglądarce
2. Powinieneś zobaczyć Cloudflare Access login page
3. Po zalogowaniu powinieneś mieć dostęp do aplikacji

## Migracja z obecnej konfiguracji

### Obecna konfiguracja (Kubernetes)

Masz cloudflared w Kubernetes, który tuneluje ruch do serwisów w klastrze.

### Nowa konfiguracja (Cloud Run)

1. **Zatrzymaj stary tunnel** (opcjonalnie, jeśli używasz tego samego domain)
2. **Utwórz nowy tunnel** dla Cloud Run
3. **Zaktualizuj route** w Cloudflare, aby wskazywał na Cloud Run
4. **Zaktualizuj Cloudflare Access** policy, aby obejmowała nowy URL

## Bezpieczeństwo

### Dodatkowe zabezpieczenia:

1. **Włącz Cloudflare WAF** (Web Application Firewall)
2. **Włącz Rate Limiting** w Cloudflare
3. **Włącz DDoS Protection**
4. **Użyj Cloudflare Access** dla autentykacji
5. **Ogranicz Cloud Run** do akceptowania tylko ruchu z Cloudflare IP ranges

### Cloud Run IAM

Upewnij się, że Cloud Run nie jest publicznie dostępne bez Cloudflare:

```bash
# Sprawdź IAM policy
gcloud run services get-iam-policy reports-app-cloudrun \
  --region=europe-west1

# Jeśli chcesz całkowicie zablokować publiczny dostęp:
# (Nie rób tego, jeśli używasz Cloudflare Tunnel - potrzebuje dostępu)
```

## Troubleshooting

### Problem: Tunnel nie łączy się

**Sprawdź:**
1. Czy token jest poprawny
2. Czy Cloud Run service ma dostęp do Secret Manager
3. Czy tunnel jest aktywny w Cloudflare Dashboard

### Problem: Cloudflare Access nie działa

**Sprawdź:**
1. Czy aplikacja jest dodana w Cloudflare Access
2. Czy policy jest poprawnie skonfigurowana
3. Czy email jest w dozwolonych domenach

### Problem: 502 Bad Gateway

**Sprawdź:**
1. Czy Cloud Run service działa: `gcloud run services describe reports-app-cloudrun`
2. Czy URL w tunnel route jest poprawny
3. Czy Cloud Run akceptuje HTTPS

## Podsumowanie

1. ✅ Utwórz Cloudflare Tunnel
2. ✅ Utwórz Cloud Run service dla cloudflared
3. ✅ Skonfiguruj route w Cloudflare
4. ✅ Skonfiguruj Cloudflare Access dla autentykacji
5. ✅ Zweryfikuj dostępność i autentykację

Po skonfigurowaniu, aplikacja będzie dostępna tylko przez Cloudflare z autentykacją.

