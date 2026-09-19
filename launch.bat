@echo off
title Gayatri AI Tutor
cd /d "%~dp0"

echo ============================================================
echo   GAYATRI AI TUTOR - Launching Application
echo ============================================================
echo.

REM ── Check venv exists ──────────────────────────────────────────
if not exist ".venv\Scripts\python.exe" (
    echo [WARN] Virtual environment (.venv) not found.
    echo Running setup.bat automatically to initialize environment...
    echo.
    call setup.bat
    if errorlevel 1 (
        echo [ERROR] Setup failed. Cannot launch Gayatri AI.
        pause
        exit /b 1
    )
)

REM ── Verify model existence via Python ───────────────────────────
.venv\Scripts\python.exe -c "from core.providers.local import LocalProvider; exit(0 if LocalProvider.MODEL_PATH.exists() else 1)" 2>nul
if errorlevel 1 (
    echo [WARN] Local GGUF model file not found.
    echo       Expected model location: GayatriAI\models\gayatri\
    echo.
)

REM ── Launch application ─────────────────────────────────────────
echo Starting Gayatri AI...
.venv\Scripts\python.exe -m app.main
if errorlevel 1 (
    echo.
    echo [ERROR] App crashed or closed with error.
    echo Check logs at: %LOCALAPPDATA%\GayatriAI\logs\gayatri.log
    pause
)
