@echo off
title GEM Logic Heatmap
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
  echo First-time setup — installing. Please wait several minutes...
  call install.bat
)

call .venv\Scripts\activate.bat
echo.
echo Opening GEM Heatmap in your web browser...
echo Keep this window open while you use the app.
echo Close this window to stop the app.
echo.
streamlit run heatmap_app.py --server.headless true
pause
