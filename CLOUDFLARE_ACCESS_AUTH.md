# Cloudflare Access - Opcje Autentykacji

## Dostępne metody autentykacji

Cloudflare Access oferuje kilka metod autentykacji. Oto najpopularniejsze:

### 1. Email (One-time PIN) - Najprostsze

**Dla kogo:** Dla małych zespołów, szybka konfiguracja

**Jak działa:**
- Użytkownik podaje email
- Otrzymuje kod PIN na email
- Wpisuje kod i ma dostęp

**Konfiguracja:**
1. W **Policy** → **Include** → **Emails**
2. Dodaj konkretne emaile lub użyj **Emails ending in**
3. Przykład: `@twoja-firma.com` - pozwoli wszystkim z tej domeny

### 2. Google OAuth - Zalecane

**Dla kogo:** Jeśli używasz Google Workspace

**Jak działa:**
- Użytkownik klika "Sign in with Google"
- Loguje się przez Google
- Cloudflare sprawdza, czy email jest dozwolony

**Konfiguracja:**
1. W **Policy** → **Include** → **Emails ending in**
2. Wpisz: `@twoja-firma.com` (jeśli używasz Google Workspace)
3. Lub dodaj konkretne emaile Google

### 3. GitHub OAuth

**Dla kogo:** Dla zespołów developerskich

**Jak działa:**
- Użytkownik loguje się przez GitHub
- Cloudflare sprawdza, czy użytkownik jest w dozwolonej organizacji/teamie

**Konfiguracja:**
1. W **Policy** → **Include** → **GitHub Organizations**
2. Dodaj organizację GitHub

### 4. Okta / Azure AD / SAML

**Dla kogo:** Dla większych firm z SSO

**Jak działa:**
- Integracja z systemem SSO firmy
- Użytkownik loguje się przez firmowy SSO

**Konfiguracja:**
- Wymaga konfiguracji w sekcji **Identity Providers**

## Szybka konfiguracja (Email One-time PIN)

### Krok po kroku:

1. **Cloudflare Dashboard** → **Zero Trust** → **Access** → **Applications**
2. Kliknij **Add an application**
3. Wybierz **Self-hosted**
4. Wypełnij:
   - **Application name**: `Reports App`
   - **Application domain**: `reports.dabronet.pl`
   - **Session duration**: `24 hours` (lub inny)
5. Kliknij **Next**
6. **Policy**:
   - **Policy name**: `Authenticated Users`
   - **Action**: `Allow`
   - **Include** → Kliknij **Add a rule**
   - Wybierz **Emails ending in**
   - Wpisz: `@twoja-firma.com` (lub konkretną domenę email)
   - Lub wybierz **Emails** i dodaj konkretne emaile
7. Kliknij **Add application**

## Przykładowe konfiguracje

### Opcja 1: Wszyscy z konkretnej domeny email

```
Policy name: Company Employees
Action: Allow
Include:
  - Emails ending in: @twoja-firma.com
```

### Opcja 2: Konkretne emaile

```
Policy name: Allowed Users
Action: Allow
Include:
  - Emails: 
      - user1@example.com
      - user2@example.com
      - user3@example.com
```

### Opcja 3: Wszyscy (bez ograniczeń)

```
Policy name: Anyone
Action: Allow
Include:
  - Emails: (puste - pozwoli każdemu z email)
```

### Opcja 4: Google Workspace

```
Policy name: Google Workspace Users
Action: Allow
Include:
  - Emails ending in: @twoja-firma.com
  - Authentication method: Google (jeśli skonfigurowane)
```

## Konfiguracja przez API (automatyczna)

Jeśli używasz skryptu `setup-cloudflare-api.sh`, możesz ustawić:

```bash
export ALLOWED_EMAIL_DOMAIN="@twoja-firma.com"
./setup-cloudflare-api.sh
```

To automatycznie utworzy policy z ograniczeniem do tej domeny.

## Bezpieczeństwo

### Zalecane ustawienia:

1. **Session duration**: `24 hours` (lub krócej dla większego bezpieczeństwa)
2. **Policy**: Ogranicz do konkretnej domeny email lub listy emaili
3. **Additional policies**: Możesz dodać więcej policy (np. dla adminów)

### Przykład z wieloma policy:

```
Policy 1: Admins
  - Emails: admin1@firma.com, admin2@firma.com
  - Action: Allow

Policy 2: Employees  
  - Emails ending in: @firma.com
  - Action: Allow
```

## Troubleshooting

### Problem: "Access denied"

**Sprawdź:**
1. Czy email jest w dozwolonych w policy
2. Czy policy ma `Action: Allow`
3. Czy aplikacja jest poprawnie skonfigurowana

### Problem: Nie widzę opcji logowania

**Sprawdź:**
1. Czy aplikacja jest dodana w Access
2. Czy domain jest poprawnie skonfigurowany
3. Czy DNS wskazuje na Cloudflare

### Problem: Chcę dodać więcej użytkowników

**Rozwiązanie:**
1. Edytuj policy w aplikacji
2. Dodaj więcej emaili lub zmień na "Emails ending in"
3. Zapisz zmiany

## Rekomendacja dla Ciebie

Dla aplikacji reports-app, polecam:

1. **Email One-time PIN** - najprostsze
2. **Policy**: `Emails ending in: @twoja-firma.com` (jeśli masz firmową domenę)
3. **Lub**: Konkretne emaile, jeśli to mały zespół

Jeśli chcesz, mogę pomóc skonfigurować konkretną opcję - powiedz mi:
- Czy masz firmową domenę email?
- Ile osób będzie miało dostęp?
- Czy używasz Google Workspace lub innego SSO?

