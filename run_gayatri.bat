@echo off
title Gayatri AI Tutor - Debug Console

echo ===================================================
echo Starting Gayatri AI Tutor...
echo ===================================================

cd /d "%~dp0"

set GAYATRI_LOG_LEVEL=DEBUG
echo [INFO] Log level set to DEBUG. Detailed logs will appear below.

if not exist ".venv\Scripts\activate.bat" (
    echo [ERROR] Virtual environment not found at .venv\Scripts\activate.bat!
    pause
    exit /b 1
)

call .venv\Scripts\activate.bat
echo [INFO] Virtual environment activated.

echo [INFO] Launching application...
python -m app.main

echo.
echo Application closed.
pause
