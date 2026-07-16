@echo off
cd /d "%~dp0"

if not exist "node_modules" (
  echo Frontend packages were not found.
  echo Please reinstall the frontend dependencies.
  pause
  exit /b 1
)

if not exist "%ProgramFiles%\nodejs\npm.cmd" (
  echo Node.js was not found.
  pause
  exit /b 1
)

title Stock Insight Web
call "%ProgramFiles%\nodejs\npm.cmd" run dev -- --host 127.0.0.1

