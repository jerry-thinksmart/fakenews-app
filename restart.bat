@echo off
echo Stopping any running Flask process...
taskkill /F /IM python.exe /T 2>nul
timeout /t 1 /nobreak >nul
echo Starting Flask app...
cd /d "%~dp0"
call .venv\Scripts\activate
python app.py
