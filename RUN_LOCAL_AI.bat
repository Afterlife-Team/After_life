@echo off
setlocal
cd /d "%~dp0"
set "AFTERLIFE_PYTHON=%USERPROFILE%\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"
if not exist "%AFTERLIFE_PYTHON%" (
  echo The verified Python runtime was not found. Please contact the project maintainer.
  pause
  exit /b 1
)
echo Starting 404 Afterlife. Keep this window open.
echo Open http://127.0.0.1:8501 in your browser.
"%AFTERLIFE_PYTHON%" "%~dp0run_local_ai.py"
if errorlevel 1 pause
