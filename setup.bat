@echo off
REM Pehli baar ka setup: venv, Python packages, npm packages, .env file.
cd /d %~dp0
if not exist venv python -m venv venv
call venv\Scripts\activate
pip install -r backend\requirements.txt
call npm install
if not exist backend\.env copy backend\.env.example backend\.env
echo.
echo Setup khatam. Ab backend\.env kholo aur DB_USER, DB_PASSWORD, DJANGO_SECRET_KEY bharo.
echo Phir README.md ka "Step 3" (database + migrate) karo.