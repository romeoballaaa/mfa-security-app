# MFA Security Web Application

Aplikacion web që demonstron dhe analizon Multi-Factor Authentication (MFA) me
Time-Based One-Time Password (TOTP) për rritjen e sigurisë së autentikimit.

Projekt praktik për temën e diplomës Master i Shkencave në Shkenca Kompjuterike,
Universiteti POLIS.

## Përmbledhje

Sistemi kombinon dy faktorë autentikimi:

- **Faktori 1:** Username ose Email + Password
- **Faktori 2:** Kod TOTP nga Google Authenticator, Microsoft Authenticator, Authy
  ose çdo aplikacion kompatibël me standardin TOTP (RFC 6238)

Përveç autentikimit, aplikacioni ofron monitorim, auditim dhe një dashboard
administrativ me statistika, si dhe një modul eksperimental për mbledhjen e të
dhënave mbi sjelljen e autentikimit nën skenarë të kontrolluar.

## Veçoritë

- Regjistrim me validim fjalëkalimi dhe hashing (PBKDF2-SHA256)
- Login me username ose email, me mesazh gjenerik kundër user enumeration
- Aktivizim MFA me QR code dhe verifikim të kodit të parë
- Recovery codes njëpërdorimshe (10 kode, të ruajtura si hash)
- Çaktivizim dhe rigjenerim me re-authentication (fjalëkalim + TOTP)
- Mbrojtje anti-replay për kodet TOTP
- Bllokim ndaj brute-force sipas llogarisë dhe IP-së (i konfigurueshëm)
- Audit log i pandryshueshëm i eventeve të sigurisë
- Dashboard për përdoruesin dhe dashboard administrativ me Chart.js
- Autorizim me role (USER / ADMIN), i zbatuar server-side
- Security headers: CSP, X-Frame-Options, HSTS (production), Permissions-Policy
- Konfigurime të ndara për development, production dhe testim

## Teknologjitë

| Komponenti | Teknologjia |
|---|---|
| Backend | Python 3.12, Django 5.2 LTS |
| Database | PostgreSQL 17 |
| Frontend | Django Templates, HTML5, CSS3, Bootstrap 5.3 |
| MFA | pyotp (TOTP), qrcode |
| Enkriptim | cryptography (Fernet) |
| Grafikë | Chart.js 4.4 |
| Testim | Django TestCase, coverage |

## Arkitektura

Django MVT me një shtresë shërbimesh (services) të ndarë nga view-t.
Logjika e sigurisë (TOTP, lockout, audit) qëndron te services, ndërsa view-t
mbeten të holla dhe të testueshme.

Modulet:

- **accounts** — User model, roles, registration, login, profil
- **mfa** — TOTP, enkriptimi i secret-it, QR, recovery codes
- **security** — LoginAttempt, lockout, security headers
- **audit** — SecurityEvent (regjistër i pandryshueshëm)
- **dashboard** — historiku dhe dashboard-i administrativ
- **research** — komanda e eksperimenteve A-H

## Instalimi

### Parakushtet

- Python 3.12 ose më i ri
- PostgreSQL 17
- Git

### 1. Klono projektin

    git clone <url-e-repository>
    cd mfa-security-app

### 2. Krijo dhe aktivizo virtual environment

Windows:

    python -m venv venv
    .\venv\Scripts\Activate.ps1

macOS / Linux:

    python3 -m venv venv
    source venv/bin/activate

### 3. Instalo varësitë

    pip install -r requirements.txt

### 4. Krijo databazën

Në psql, si përdoruesi postgres:

    CREATE DATABASE mfa_security_db;
    CREATE USER mfa_user WITH PASSWORD 'zgjidh-nje-fjalekalim';
    ALTER DATABASE mfa_security_db OWNER TO mfa_user;
    ALTER ROLE mfa_user CREATEDB;

### 5. Konfiguro .env

Kopjo shabllonin:

    copy .env.example .env

Gjenero SECRET_KEY:

    python -c "import secrets,string; print(''.join(secrets.choice(string.ascii_letters+string.digits) for _ in range(64)))"

Gjenero çelësin e enkriptimit MFA:

    python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"

Vendos të dyja vlerat te .env, si dhe DATABASE_URL me fjalëkalimin e mfa_user.

### 6. Ekzekuto migrimet

    python manage.py migrate

### 7. Krijo një administrator

    python manage.py createsuperuser

### 8. Nis serverin

    python manage.py runserver

Aplikacioni hapet te http://127.0.0.1:8000/

## Aktivizimi i MFA

1. Kyçu dhe shko te Profili
2. Kliko "Aktivizo MFA"
3. Skano QR code-in me aplikacionin authenticator
4. Fut kodin e parë 6-shifror për ta konfirmuar
5. Ruaj recovery codes që shfaqen

## Testimi

    python manage.py test --settings=config.settings.test

Me raport mbulimi:

    coverage run manage.py test --settings=config.settings.test
    coverage report
    coverage html

## Eksperimentet

Skenarët A-H ekzekutohen vetëm kundër aplikacionit lokal, me llogari testimi:

    python manage.py run_experiments --settings=config.settings.research

Rezultatet ruhen në research/results/ si CSV dhe JSON.

## Shënime sigurie

- Sekretet (SECRET_KEY, fjalëkalimi i databazës, çelësi MFA) ruhen vetëm te .env,
  i cili nuk versionohet kurrë.
- Fjalëkalimet ruhen si hash PBKDF2-SHA256, kurrë plain-text.
- Secret-i TOTP ruhet i enkriptuar me Fernet, jo si hash, sepse serveri duhet ta
  rilexojë për të llogaritur kodin.
- Recovery codes ruhen si hash HMAC-SHA256.
- Audit log-u nuk ruan kurrë fjalëkalime, secret-e, OTP apo recovery codes.

## Development vs Production

| Cilësimi | Development | Production |
|---|---|---|
| DEBUG | True | False |
| Secure cookies | False (HTTP lokal) | True (HTTPS) |
| HSTS | Jo aktiv | Aktiv |
| Settings module | config.settings.dev | config.settings.prod |

Në production, verifiko konfigurimin me:

    python manage.py check --deploy --settings=config.settings.prod

## Struktura e projektit

    mfa-security-app/
    ├── config/          # settings (base/dev/prod/test/research), urls, wsgi
    ├── accounts/        # User model, registration, login, profil
    ├── mfa/             # TOTP, QR, recovery codes, services
    ├── security/        # lockout, middleware, LoginAttempt
    ├── audit/           # SecurityEvent, record_event
    ├── dashboard/       # historiku dhe dashboard administrativ
    ├── research/        # komanda e eksperimenteve A-H
    ├── templates/       # HTML (base, partials, faqet)
    ├── static/          # CSS, JS, Bootstrap dhe Chart.js lokal
    ├── docs/            # DEVLOG, screenshots, diagrame
    ├── requirements.txt
    └── manage.py
