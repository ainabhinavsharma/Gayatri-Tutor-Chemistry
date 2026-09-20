@echo off
title Gayatri AI Tutor - Debug Console
cd /d "%~dp0"

echo ============================================================
echo   GAYATRI AI TUTOR - Debug Mode
echo ============================================================
echo.

set GAYATRI_LOG_LEVEL=DEBUG
echo [INFO] Log level set to DEBUG. Detailed logs will appear below.

if not exist .venv\Scripts\python.exe call setup.bat
if not exist .venv\Scripts\python.exe (
    echo [ERROR] Virtual environment setup failed.
    pause
    exit /b 1
)

echo [INFO] Launching application...
.venv\Scripts\python.exe -m app.main

echo.
echo Application closed.
pause
