@echo off
title Gayatri AI Tutor - Setup and Installer
cd /d "%~dp0"
echo.
echo ============================================================
echo   GAYATRI AI - Setup and Initialization
echo ============================================================
echo.

REM Check Python
echo [1/4] Checking Python installation...
python --version >nul 2>&1
if errorlevel 1 (
    py --version >nul 2>&1
    if errorlevel 1 (
        echo [ERROR] Python not found. Please install Python 3.10, 3.11, or 3.12 from python.org
        pause
        exit /b 1
    )
    set "PYTHON=py"
) else (
    set "PYTHON=python"
)

%PYTHON% --version
echo [OK] Python found.

REM Check/create venv
echo.
echo [2/4] Checking virtual environment (.venv)...
if exist .venv\Scripts\python.exe (
    echo [OK] Virtual environment exists.
) else (
    echo       Creating virtual environment (.venv)...
    %PYTHON% -m venv .venv
    if errorlevel 1 (
        echo [ERROR] Failed to create virtual environment (.venv).
        pause
        exit /b 1
    )
    echo [OK] Virtual environment created.
)

REM Install dependencies
echo.
echo [3/4] Installing dependencies from requirements.txt...
.venv\Scripts\pip.exe install -r requirements.txt
if errorlevel 1 (
    echo.
    echo [ERROR] pip install failed. Please check your internet connection or requirements.txt
    pause
    exit /b 1
)

REM Verify llama-cpp-python installation
.venv\Scripts\python.exe -c "import llama_cpp; print('[OK] llama-cpp-python loaded successfully')" 2>nul
if errorlevel 1 (
    echo.
    echo       llama-cpp-python compilation / build check...
    .venv\Scripts\python.exe install_llama.py
    if errorlevel 1 (
        echo [WARN] llama-cpp-python compilation fell back to prebuilt wheel.
    )
)

REM Verify model
echo.
echo [4/4] Checking model file status...
.venv\Scripts\python.exe -c "from core.providers.local import LocalProvider; print('[OK] Model detected at:', LocalProvider.MODEL_PATH); import sys; sys.exit(0 if LocalProvider.MODEL_PATH.exists() else 1)"
if errorlevel 1 (
    echo.
    echo [WARN] Local model file not detected yet.
    echo       Place your GGUF model in: GayatriAI\models\gayatri
    echo.
    echo       The app will still launch, but local AI responses require a model.
)

echo.
echo ============================================================
echo   Setup Complete! Launching Gayatri AI...
echo ============================================================
echo.

.venv\Scripts\python.exe -m app.main
if errorlevel 1 (
    echo.
    echo [ERROR] Application exited with error.
    echo Check logs at: %LOCALAPPDATA%\GayatriAI\logs\gayatri.log
    pause
)
