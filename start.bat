@echo off
title MFA Security App
cd /d "%~dp0"

echo ============================================
echo   MFA Security App - duke u nisur...
echo ============================================
echo.

if not exist "venv\Scripts\activate.bat" (
    echo [GABIM] Nuk u gjet virtual environment "venv".
    echo Krijoje me: python -m venv venv
    echo dhe instalo varesite: pip install -r requirements.txt
    pause
    exit /b 1
)

if not exist ".env" (
    echo [GABIM] Mungon file-i .env
    echo Kopjo .env.example si .env dhe ploteso vlerat.
    pause
    exit /b 1
)

call venv\Scripts\activate.bat

sc query postgresql-x64-17 | find "RUNNING" >nul
if errorlevel 1 (
    echo [KUJDES] PostgreSQL nuk po punon. Po provoj ta nis...
    net start postgresql-x64-17 >nul 2>&1
    if errorlevel 1 (
        echo [GABIM] PostgreSQL nuk u nis dot.
        echo Nise nga Services: postgresql-x64-17 - Start
        echo ose hape kete file me "Run as administrator".
        pause
        exit /b 1
    )
)

echo [OK] Virtual environment aktiv
echo [OK] PostgreSQL po punon
echo.

python manage.py migrate --noinput
if errorlevel 1 (
    echo [GABIM] Migrimet deshtuan. Kontrollo .env dhe databazen.
    pause
    exit /b 1
)

echo.
echo Aplikacioni do te hapet ne browser pas pak sekondash:
echo   http://127.0.0.1:8000/
echo.
echo Per ta ndaluar serverin: mbyll kete dritare ose shtyp Ctrl+C
echo ============================================
echo.

start "" cmd /c "timeout /t 4 /nobreak >nul && start http://127.0.0.1:8000/"

python manage.py runserver

pause