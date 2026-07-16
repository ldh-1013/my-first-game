@echo off
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
  echo Python virtual environment was not found.
  echo Please reinstall the backend dependencies.
  pause
  exit /b 1
)

title Stock Insight API
".venv\Scripts\python.exe" -m uvicorn app.main:app --host 127.0.0.1 --port 8010
