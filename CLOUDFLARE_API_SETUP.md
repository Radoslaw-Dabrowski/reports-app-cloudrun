# Konfiguracja Cloudflare przez API

## Wymagania

1. **Cloudflare API Token** z uprawnieniami:
   - Account: Cloudflare Workers:Edit
   - Zone: Zone:Read, DNS:Edit
   - Account: Access: Applications and Policies:Edit

2. **Cloudflare Account ID** - znajdziesz w prawym panelu Cloudflare Dashboard

3. **Domena** zarządzana przez Cloudflare

## Szybki start

### Opcja 1: Bash script

```bash
export CLOUDFLARE_API_TOKEN="your-api-token"
export CLOUDFLARE_ACCOUNT_ID="your-account-id"
export DOMAIN="twoja-domena.com"
export SUBDOMAIN="reports"  # opcjonalne, domyślnie "reports"
export ALLOWED_EMAIL_DOMAIN="@twoja-firma.com"  # opcjonalne

./setup-cloudflare-api.sh
```

### Opcja 2: Python script

```bash
export CLOUDFLARE_API_TOKEN="your-api-token"
export CLOUDFLARE_ACCOUNT_ID="your-account-id"
export DOMAIN="twoja-domena.com"
export SUBDOMAIN="reports"  # opcjonalne
export ALLOWED_EMAIL_DOMAIN="@twoja-firma.com"  # opcjonalne

python3 setup-cloudflare-api-python.py
```

## Jak uzyskać API Token

1. Zaloguj się do [Cloudflare Dashboard](https://dash.cloudflare.com)
2. Przejdź do **My Profile** → **API Tokens**
3. Kliknij **Create Token**
4. Użyj **Edit Cloudflare Workers** template lub utwórz custom token z uprawnieniami:
   - **Account** → **Cloudflare Workers** → **Edit**
   - **Zone** → **Zone** → **Read**, **DNS** → **Edit**
   - **Account** → **Access: Applications and Policies** → **Edit**
5. Skopiuj token

## Jak uzyskać Account ID

1. Zaloguj się do Cloudflare Dashboard
2. W prawym panelu znajdziesz **Account ID**
3. Skopiuj ID

## Co robi skrypt

1. ✅ Pobiera Zone ID dla domeny
2. ✅ Tworzy Cloudflare Worker z kodem proxy
3. ✅ Bindowuje custom domain do worker
4. ✅ Tworzy Cloudflare Access Application z autentykacją
5. ✅ Konfiguruje policy dostępu

## Przykładowe użycie

```bash
# Podstawowe użycie
export CLOUDFLARE_API_TOKEN="abc123..."
export CLOUDFLARE_ACCOUNT_ID="def456..."
export DOMAIN="example.com"
./setup-cloudflare-api.sh

# Z ograniczeniem do konkretnej domeny email
export ALLOWED_EMAIL_DOMAIN="@firma.com"
./setup-cloudflare-api.sh

# Z custom subdomain
export SUBDOMAIN="moje-raporty"
./setup-cloudflare-api.sh
```

## Weryfikacja

Po uruchomieniu skryptu:

1. **Sprawdź Worker:**
   ```bash
   curl https://api.cloudflare.com/client/v4/accounts/$CLOUDFLARE_ACCOUNT_ID/workers/scripts/$WORKER_NAME \
     -H "Authorization: Bearer $CLOUDFLARE_API_TOKEN"
   ```

2. **Sprawdź dostępność:**
   ```bash
   curl -I https://reports.twoja-domena.com
   ```

3. **Sprawdź autentykację:**
   - Otwórz `https://reports.twoja-domena.com` w przeglądarce
   - Powinieneś zobaczyć Cloudflare Access login page

## Troubleshooting

### Błąd: "Domain not found in Cloudflare"

**Rozwiązanie:** Upewnij się, że domena jest zarządzana przez Cloudflare i że używasz poprawnej nazwy domeny.

### Błąd: "Invalid API token"

**Rozwiązanie:** Sprawdź, czy token ma wszystkie wymagane uprawnienia.

### Błąd: "Worker already exists"

**Rozwiązanie:** To nie jest błąd - skrypt zaktualizuje istniejącego worker.

### Access Application nie działa

**Rozwiązanie:** Sprawdź w Cloudflare Dashboard → Zero Trust → Access → Applications, czy aplikacja została utworzona. Jeśli nie, utwórz ręcznie.

## Ręczna konfiguracja (jeśli API nie działa)

Jeśli skrypt nie działa, możesz skonfigurować ręcznie:

1. **Worker:** Cloudflare Dashboard → Workers & Pages → Create Worker
2. **Route:** Worker → Settings → Triggers → Add Custom Domain
3. **Access:** Zero Trust → Access → Applications → Add application

Szczegóły w `setup-cloudflare-workers.md`.

