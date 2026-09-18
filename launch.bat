@echo off
cd /d "%~dp0"

REM ── Check venv exists ──────────────────────────────────────────
if not exist ".venv\Scripts\python.exe" (
    echo [ERROR] Virtual environment not found.
    echo       Run setup.bat first.
    pause
    exit /b 1
)

REM ── Check model exists ─────────────────────────────────────────
set "RUNTIME_MODEL=%LOCALAPPDATA%\GayatriAI\models\gayatri\gemma-2-2b-it-IQ3_M.gguf"
set "PROJECT_MODEL=GayatriAI\models\gayatri\gemma-2-2b-it-IQ3_M.gguf"

if not exist "%RUNTIME_MODEL%" (
    if not exist "%PROJECT_MODEL%" (
        echo [ERROR] Model file not found.
        echo       Place gemma-2-2b-it-IQ3_M.gguf in either:
        echo       - %RUNTIME_MODEL%
        echo       - %PROJECT_MODEL%
        pause
        exit /b 1
    )
)

.venv\Scripts\python.exe -m app.main
if errorlevel 1 (
    echo.
    echo [ERROR] App crashed. Check GayatriAI\logs\gayatri.log for details.
    pause
)
