# Development Log

## Phase 1 — Environment

- Python 3.12.6, Django 5.2 LTS (security support deri në prill 2028), Windows.
- Virtual environment për izolim dhe riprodhueshmëri.
- `.gitignore` i krijuar para commit-it të parë.
- Alternativa: Django 6.0 (refuzuar: cikël mbështetjeje më i shkurtër se jeta e projektit).

## Phase 2A — Settings dhe environment variables

- Settings të ndara: `base`, `dev`, `prod`, `test`.
- Sekretet në `.env` me `django-environ`; `.env.example` pa vlera reale.
- `SECRET_KEY` u rrotullua pas commit-it të parë, sepse çelësi fillestar mbeti në historikun e Git.
- `SECRET_KEY` alfanumerik 64-karakterësh, për të shmangur probleme parsimi të `.env`.
- Session: HttpOnly, SameSite=Lax, skadim pas 30 minutash, skadim me mbylljen e browser-it.
- Test settings përdorin hasher të shpejtë vetëm për suitën e testeve.

## Phase 2B — Database

- PostgreSQL 17 me përdorues të dedikuar `mfa_user` (privilegj minimal, pronar vetëm i databazës së aplikacionit).
- Fjalëkalimi i përdoruesit u vendos me `\password` (nuk ruhet në historikun e komandave).
- Isolation level: read committed. Timezone: Europe/Tirane.
- Alternativa: SQLite (refuzuar: nuk mbështet `select_for_update` për testet e konkurrencës).

## Phase 2C — Templates dhe static files

- `base.html` me partials për navbar, mesazhe dhe footer.
- Bootstrap 5.3.8 i shërbyer lokalisht (jo CDN) për CSP strikte dhe demo offline.
- Asnjë stil ose skript inline, për të shmangur `'unsafe-inline'` në CSP.
- Security headers të verifikuara me `Invoke-WebRequest`: X-Frame-Options, nosniff, Referrer-Policy. HSTS mungon me qëllim në dev.

## Problemet e hasura

- PowerShell execution policy bllokoi aktivizimin e venv: zgjidhur me `RemoteSigned` për CurrentUser.
- File-t e settings-eve u krijuan bosh: Django ngarkoi vlerat e parazgjedhura (`DEBUG=False`, `ALLOWED_HOSTS=[]`).
- PostgreSQL jo në PATH pas instalimit: shtuar manualisht.
- Git "dubious ownership": folderi në pronësi të Administrators; zgjidhur me `safe.directory` vetëm për këtë repository.