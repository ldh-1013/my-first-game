@echo off
set "ROOT=%~dp0"

echo Starting Stock Insight AI...
start "Stock Insight API" /D "%ROOT%backend" cmd.exe /k call run-backend.bat
start "Stock Insight Web" /D "%ROOT%frontend" cmd.exe /k call run-frontend.bat

echo Waiting for local servers...
timeout /t 5 /nobreak >nul
start "" "http://127.0.0.1:5173"

echo Browser opened.
echo Close the API and Web windows to stop the application.
timeout /t 3 /nobreak >nul

