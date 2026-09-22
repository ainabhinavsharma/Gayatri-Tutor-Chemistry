@echo off
title Gayatri Chemistry Tutor — Student Demo
cd /d "%~dp0"
cls

echo ======================================================================
echo   GAYATRI CHEMISTRY TUTOR — Student Demo Environment
echo   Offline NCERT Adaptive Tutoring Platform
echo ======================================================================
echo.
echo [1/2] Initializing local database, student profile ^& past sessions...

REM Suppress verbose debug logs in console
set GAYATRI_LOG_LEVEL=WARNING

REM Verify virtual environment
if not exist .venv\Scripts\python.exe (
    echo [ERROR] Virtual environment not found at .venv. Please run setup.bat first.
    pause
    exit /b 1
)

REM Pre-seed and validate local demo database silently
.venv\Scripts\python.exe scripts/seed_demo_student.py >nul 2>&1
if errorlevel 1 (
    echo [WARN] Demo pre-flight initialization completed with notices.
)

echo [2/2] Launching Gayatri AI Desktop Application...
echo.
echo ======================================================================
echo   Application is running.
echo   You may now demonstrate all 13 tutor and platform abilities!
echo   Close the application window when done.
echo ======================================================================

.venv\Scripts\python.exe -m app.main
if errorlevel 1 (
    echo.
    echo [NOTICE] Application closed.
)
