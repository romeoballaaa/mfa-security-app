# Komandat e terminalit — MFA Security App

Të gjitha komandat ekzekutohen në terminalin e VS Code, brenda folderit
`C:\Projects\mfa-security-app`, me `(venv)` në fillim të rreshtit.

---

## 1. Fillimi i punës (çdo herë që hap projektin)

Aktivizo virtual environment (nëse nuk aktivizohet vetë):

    .\venv\Scripts\Activate.ps1

Shenja që u aktivizua: prompt-i fillon me `(venv)`.

Nëse Windows refuzon me "running scripts is disabled", ekzekuto një herë:

    Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned

---

## 2. Serveri

Nis serverin (aplikacioni hapet te http://127.0.0.1:8000/):

    python manage.py runserver

Ndalo serverin: shtyp Ctrl+C në terminal.

Terminali "ngec" pas runserver? Nuk është ngecje — serveri po punon.
Për komanda të tjera ndërkohë, hap terminal të dytë me butonin + në panelin e terminalit.

---

## 3. Databaza dhe migrimet

Krijo migrimet pas çdo ndryshimi te models.py:

    python manage.py makemigrations

Zbato migrimet në databazë:

    python manage.py migrate

Hyr në databazë (PostgreSQL) për të parë tabelat:

    python manage.py dbshell

Brenda dbshell:
    \dt              -- liston tabelat
    \d emri_tabeles  -- struktura e nje tabele
    \q               -- dil

Krijo një administrator:

    python manage.py createsuperuser

Ndrysho fjalëkalimin e një përdoruesi:

    python manage.py changepassword emri_i_userit

---

## 4. Kontrolli i kodit

Kontrollo për gabime pa nisur serverin:

    python manage.py check

Kontrollo konfigurimin e production-it (siguria):

    python manage.py check --deploy --settings=config.settings.prod

---

## 5. Testet

Ekzekuto të gjitha testet:

    python manage.py test --settings=config.settings.test --noinput

Testet me detaje (çdo test me emër):

    python manage.py test --settings=config.settings.test --noinput -v 2

Ruaj rezultatet e testeve në file:

    python manage.py test --settings=config.settings.test --noinput -v 2 2>&1 | Tee-Object docs\test-results.txt

Mbulimi i kodit nga testet (coverage):

    coverage run manage.py test --settings=config.settings.test --noinput
    coverage report
    coverage html

Raporti vizual: hap docs\..\htmlcov\index.html në browser.

---

## 6. Eksperimentet (Phase 9)

Ekzekuto skenarët A-H (vetëm lokal, me llogari testimi):

    python manage.py run_experiments --settings=config.settings.research

Rezultatet ruhen në research\results\ si CSV dhe JSON.

Shiko file-in e fundit CSV:

    Get-ChildItem research\results\*.csv | Select-Object -Last 1 | Get-Content

---

## 7. Git

Shiko gjendjen (çfarë ka ndryshuar):

    git status

Shto të gjitha ndryshimet:

    git add .

Bëj commit me përshkrim:

    git commit -m "Pershkrimi i ndryshimit"

Shiko historikun e commit-eve:

    git log --oneline

Kontrollo që .env NUK është në Git (duhet të dalë vetëm .env.example):

    git ls-files | Select-String "\.env"

---

## 8. Paketat (pip)

Instalo një paketë të re:

    python -m pip install emri_i_paketes

Shiko versionet e paketave kryesore:

    pip show django django-environ psycopg pyotp qrcode cryptography | Select-String "Name|Version"

Rikrijo listën e varësive (kujdes: prish komentet, përdore vetëm nëse e di ç'bën):

    python -m pip freeze > requirements_full.txt

---

## 9. File dhe foldera (PowerShell)

Shiko ku ndodhesh:

    pwd

Liston përmbajtjen e një folderi:

    Get-ChildItem emri_folderit -Name

Krijo një file bosh:

    New-Item shtegu\emri.py -ItemType File

Krijo një folder:

    mkdir emri_folderit

---

## 10. Situata të zakonshme

**"No module named django"** → venv nuk është aktiv:

    .\venv\Scripts\Activate.ps1

**"could not connect to server" (databaza)** → PostgreSQL nuk po punon:

    Start-Service postgresql-x64-17

**Të gjitha login-et bllokohen gjatë testimit** → pastro tentativat:

    python manage.py shell -c "from security.models import LoginAttempt; LoginAttempt.objects.filter(success=False).delete()"

**Zhblloko një llogari** → nga admin-i: Users → zgjidh → Action "Zhblloko" → Go

---

## Përmbledhje: puna e përditshme

1. Hap VS Code te projekti
2. Aktivizo venv:            .\venv\Scripts\Activate.ps1
3. Nis serverin:            python manage.py runserver
4. Puno / testo
5. Ndalo serverin:          Ctrl+C
6. Ruaj në Git:             git add .  →  git commit -m "..."