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
## Phase 3A — User model dhe audit

- Custom User (`AbstractUser`) me `email` unik dhe `role` (USER/ADMIN).
- Email dhe username normalizohen para ruajtjes (lowercase, strip).
- `SecurityEvent`: regjistër i pandryshueshëm; admin pa add/change/delete.
- `SET_NULL` te audit log: eventet mbeten edhe pas fshirjes së user-it.
- Metadata me listë të bardhë çelësash: sekretet nuk mund të regjistrohen as gabimisht.
- IP nga `REMOTE_ADDR`, jo nga `X-Forwarded-For` (i falsifikueshëm).
- Fjalëkalimet: PBKDF2-SHA256 me salt dhe iteracione të larta (verifikuar në databazë).

## Phase 3B — Regjistrimi

- Zgjerim i `UserCreationForm`: hashing dhe validatorët nga Django.
- Unicitet pa dallim shkronjash (`iexact`) për username dhe email.
- Pa auto-login pas regjistrimit: session krijohet vetëm te login-i.
- Test CSRF: forma pa token → 403, llogaria nuk krijohet (screenshot).
- Kufizim i pranuar: regjistrimi zbulon nëse një email ekziston (enumeration). Alternativa kërkon verifikim me email, jashtë scope-it.

## Phase 3C — Login dhe logout

- Backend që pranon username ose email.
- Hash i kotë kur user-i nuk ekziston: barazon kohën e përgjigjes.
- Mesazh i vetëm gabimi për çdo dështim: pa enumeration në login.
- `identifier_hint` i maskuar në audit (3 karaktere + gjatësia).
- `LOGIN_FAILED` nuk lidhet me user-in.
- `login()` rrotullon session key (session fixation).
- Logout vetëm me POST.
- `never_cache` mbi faqet e mbrojtura.

## Phase 4A — Modelet e MFA

- Secret TOTP i enkriptuar me Fernet (AES-128-CBC + HMAC-SHA256), jo hash, sepse serveri duhet ta rilexojë.
- `MultiFernet` për rotacion çelësash.
- Çelësi në `.env` (`MFA_ENCRYPTION_KEYS`), jashtë databazës.
- I njëjti secret jep tekst të enkriptuar të ndryshëm çdo herë (IV i rastësishëm).
- Manipulimi i tekstit të enkriptuar zbulohet (`InvalidToken`).
- `CheckConstraint`: pajisje e konfirmuar ka gjithmonë `confirmed_at`.
- `CASCADE` për kredencialet MFA, ndryshe nga audit log.
- Admin nuk shfaq secret-in dhe hash-et e recovery codes.
- Alternativa: `django-otp` (refuzuar: duam kontroll mbi audit, metrika, anti-replay).

## Phase 4B — Aktivizimi i MFA

- TOTP sipas RFC 6238 me `pyotp`; testuar me Google Authenticator.
- MFA aktive vetëm pas verifikimit të kodit të parë.
- I njëjti secret rishfaqet deri në konfirmim.
- Dritare ±1 hap: probabilitet teorik 3/10⁶ për hamendësim. Duhet matur eksperimentalisht.
- `hmac.compare_digest` për krahasim në kohë konstante.
- Anti-replay atomik: `UPDATE ... WHERE last_used_step < X`.
- QR si data URI brenda `<img>`: pa ekzekutim skriptesh, pa file në disk.
- `never_cache` i detyrueshëm në faqen e setup.
- Dështimet e setup regjistrohen me `stage: SETUP`, të ndara nga ato të login-it.
- Gjendje e përkohshme: MFA aktive në databazë, por login-i nuk e kërkon ende (zgjidhet në 4C).

## Problemet e hasura (vazhdim)

- `IndentationError` te `views.py` dhe `forms.py` pas kopjimit të kodit.
- Faqja e regjistrimit ridrejtonte te Home: përdoruesi ishte i kyçur nga admin (sjellje e qëllimshme).
- Butoni Back pas logout shfaqte profilin nga cache-i i browser-it; zgjidhur me `never_cache`.
## Phase 4C — Login me dy faktorë

- Pas fjalëkalimit për user me MFA nuk thirret `login()`; session ruan vetëm gjendjen pre-MFA.
- `login_required` bllokon çdo faqe të mbrojtur deri te TOTP.
- Sfida skadon pas 300 s dhe anulohet pas 5 kodesh të gabuara.
- Replay dhe kod i gabuar: i njëjti mesazh për përdoruesin, `reason` i ndryshëm në audit.
- `duration_ms`: koha nga fjalëkalimi deri te TOTP-ja e pranuar.
- Dobësi e gjetur dhe e mbyllur: `/admin/login/` anashkalonte MFA. Ridrejtuar te login-i ynë.
- Test: pas fjalëkalimit, qasje direkte te profili → ridrejtim te login-i.
## Phase 4D — Recovery codes dhe çaktivizimi

- 10 kode njëpërdorimshe, 10 karaktere (~49 bita entropi), gjeneruar me `secrets`.
- Ruhen si HMAC-SHA256 (`salted_hmac` i Django-s), jo PBKDF2: kodet kanë entropi të lartë, jo si fjalëkalimet.
- Shfaqen vetëm një herë, direkt në përgjigje; nuk ruhen askund të lexueshëm.
- Përdorimi atomik: `UPDATE ... WHERE used_at IS NULL`.
- Rigjenerimi i pavlefëson kodet e vjetra.
- Login me recovery code kalon nga e njëjta sfidë dhe i njëjti kufi tentativash si TOTP.
- Çaktivizimi dhe rigjenerimi kërkojnë fjalëkalim + TOTP (re-authentication).
- Kufizim: rotacioni i `SECRET_KEY` pavlefëson recovery codes ekzistuese.
## Phase 5 — Mbrojtja nga brute-force dhe siguria e session-it

- `LoginAttempt` i ndarë nga audit log: të dhëna operacionale për lockout.
- Lockout: 5 dështime / 15 min për llogari; 20 / 15 min për IP (configurable).
- Identifikues kanonik: username dhe email i së njëjtës llogari numërohen bashkë.
- Identifikuesit e llogarive që s'ekzistojnë ruhen si HMAC, jo tekst i lexueshëm.
- "Regjistro pastaj numëro": pa numërues në memorie.
- Reset vetëm pas autentikimit të plotë: fjalëkalimi i saktë nuk reseton numëruesin për llogari me MFA.
- Gjatë bllokimit fjalëkalimi nuk verifikohet fare; tentativat e bllokuara nuk e zgjasin bllokimin.
- Bllokimi zbatohet njëlloj për llogari që s'ekzistojnë: pa enumeration.
- Zhbllokim manual nga admin → `ACCOUNT_UNLOCKED`. Skadimi natyral nuk gjeneron event.
- Kufizim i njohur: me kërkesa të njëkohshme, pragu mund të kalohet me 1–2 tentativa.
- Kufizim i njohur: lockout-i i llogarisë mund të përdoret si DoS ndaj përdoruesit legjitim.
- Ndryshimi i fjalëkalimit mbyll session-et e tjera (`update_session_auth_hash`).
- `SESSION_SAVE_EVERY_REQUEST`: 30 min si idle timeout.
- CSP: `'self'` për skripte dhe stile; `img-src data:` për QR dhe ikonat e Bootstrap.
- Permissions-Policy: kamera, mikrofoni, vendndodhja të çaktivizuara.
- `admin_required`: kontroll server-side i rolit; regjistron `UNAUTHORIZED_ACCESS`.
## Phase 6 — Historiku i sigurisë

- Faqe me të gjitha eventet e përdoruesit, me filtër dhe pagination (25/faqe).
- Filtri pranon vetëm vlera nga lista e eventeve; çdo vlerë tjetër injorohet.

## Phase 7 — Dashboard-et

- Admin Security Dashboard: vetëm për rolin ADMIN (`admin_required`, server-side).
- Statistikat llogariten nga audit log-u dhe `MFADevice`; dashboard-i nuk ka tabela të veta.
- Tentativat e bllokuara numërohen veçmas nga dështimet e zakonshme.
- MFA adoption rate, koha mesatare MFA (nga `duration_ms`).
- Chart.js 4.4.1 lokal; të dhënat me `json_script` → CSP mbetet `script-src 'self'`.
- 4 grafikë: MFA aktive/joaktive, autentikime sipas rezultatit, login-e në 14 ditë, evente sipas kategorisë.
- Scenario H (test manual): user pa rol ADMIN → 403 + `UNAUTHORIZED_ACCESS` me `path`.
- Shënim: "MFA adoption rate" mbi llogari testimi është parametër i mjedisit, jo gjetje kërkimore.
