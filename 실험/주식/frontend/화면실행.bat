@echo off
chcp 65001 >nul
cd /d "%~dp0"

if not exist "node_modules" (
  echo 프런트엔드 패키지를 찾을 수 없습니다.
  echo README의 프런트엔드 설치 단계를 먼저 실행해 주세요.
  pause
  exit /b 1
)

title Stock Insight Web
call "%ProgramFiles%\nodejs\npm.cmd" run dev -- --host 127.0.0.1

