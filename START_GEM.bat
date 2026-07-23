@echo off
cd /d "%~dp0"
title GEM Logic Platform
echo Starting GEM Logic Platform...
if not exist ".venv\Scripts\python.exe" (
  echo First run - installing. Please wait...
  call install.bat
)
call .venv\Scripts\activate.bat
python gem_app.py
if errorlevel 1 (
  echo.
  echo GUI failed - running terminal monitor instead...
  python scripts\run_gem_monitor.py --once
  pause
)
