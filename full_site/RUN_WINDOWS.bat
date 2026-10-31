@echo off
setlocal
cd /d "%~dp0"
echo =============================================
echo 404 AFTERLIFE - Start Project
 echo =============================================
if not exist ".venv\Scripts\python.exe" (
    echo Creating Python environment...
    python -m venv .venv
    if errorlevel 1 (
        echo Could not create environment. Install Python 3.11 or newer and ensure it is on PATH.
        pause
        exit /b 1
    )
)
echo Installing or updating required libraries...
".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 (
    echo Package installation failed. Check internet and Python configuration.
    pause
    exit /b 1
)
echo Running 404 Afterlife...
".venv\Scripts\python.exe" -m streamlit run app.py
pause
