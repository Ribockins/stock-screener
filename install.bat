@echo off
REM GEM Logic Platform installer (Windows)
cd /d "%~dp0"

echo ==^> GEM Logic Platform installer

where python >nul 2>&1
if errorlevel 1 (
  echo Python 3 is required. Install from https://www.python.org/ and re-run.
  exit /b 1
)

python -m venv .venv
call .venv\Scripts\activate.bat
python -m pip install --upgrade pip wheel
pip install -r requirements-platform.txt
pip install --no-cache-dir git+https://github.com/rongardF/tvdatafeed.git

python -c "import site, pathlib; p=pathlib.Path(site.getsitepackages()[0])/'tvdatafeed'; p.mkdir(exist_ok=True); (p/'__init__.py').write_text('from tvDatafeed import *\\n')"

if not exist .env copy .env.example .env

echo.
echo Installation complete.
echo   Desktop:  .venv\Scripts\activate ^&^& python gem_app.py
echo   CLI:      .venv\Scripts\activate ^&^& python scripts\run_gem_monitor.py --once
echo   Watchlist: config\watchlist.json
echo.
pause
