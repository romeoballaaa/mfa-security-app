@echo off
title MFA Security App - Testet
cd /d "%~dp0"

call venv\Scripts\activate.bat

echo ============================================
echo   Ekzekutimi i testeve automatike
echo ============================================
echo.

python manage.py test --settings=config.settings.test --noinput

echo.
echo ============================================
pause