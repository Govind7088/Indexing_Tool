@echo off
REM Backend aur frontend ko do alag windows mein chalata hai.
cd /d %~dp0
start "Backend (Django)" cmd /k "cd /d %~dp0backend && ..\venv\Scripts\activate && python manage.py runserver"
start "Frontend (React)" cmd /k "cd /d %~dp0 && npm run dev"
echo Dono windows khul gayi hain. Browser mein kholo: http://localhost:5173