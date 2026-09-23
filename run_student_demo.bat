@echo off
title Gayatri Chemistry Tutor — NCERT Adaptive Learning
cd /d "%~dp0"
cls

echo ======================================================================
echo   GAYATRI CHEMISTRY TUTOR — NCERT Adaptive Learning Platform
echo   100%% Offline Local Tutoring Environment
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

REM Pre-seed and validate local student database silently
.venv\Scripts\python.exe scripts/seed_demo_student.py >nul 2>&1
if errorlevel 1 (
    echo [WARN] Pre-flight initialization completed with notices.
)

REM Ensure gai3.ico and desktop shortcuts exist
if not exist "Gayatri Chemistry Tutor.lnk" (
    .venv\Scripts\python.exe scripts/create_launch_shortcuts.py >nul 2>&1
)

echo [2/2] Launching Gayatri AI Desktop Application...
echo.
echo ======================================================================
echo   Application is running.
echo   Ready for interactive chemistry tutoring and student learning.
echo   Close the application window when done.
echo ======================================================================

.venv\Scripts\python.exe -m app.main
if errorlevel 1 (
    echo.
    echo [NOTICE] Application closed.
)
