@echo off
chcp 65001 >nul
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
  echo Python 가상환경을 찾을 수 없습니다.
  echo README의 백엔드 설치 단계를 먼저 실행해 주세요.
  pause
  exit /b 1
)

title Stock Insight API
".venv\Scripts\python.exe" -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000

