@echo off
cd /d "%~dp0"
echo.
echo ============================================================
echo   GAYATRI AI - Setup and Launch
echo ============================================================
echo.

REM ── Check Python ──────────────────────────────────────────────
echo [1/5] Checking Python...
python --version >nul 2>&1
if errorlevel 1 (
    py --version >nul 2>&1
    if errorlevel 1 (
        echo [ERROR] Python not found. Install Python 3.12 (3.12.x) from python.org
        pause
        exit /b 1
    )
    set "PYTHON=py"
) else (
    set "PYTHON=python"
)

%PYTHON% --version
echo [OK] Python found

REM ── Check/create venv ─────────────────────────────────────────
echo.
echo [2/5] Checking virtual environment...
if exist ".venv\Scripts\python.exe" (
    echo [OK] .venv exists
    set "PIP=.venv\Scripts\pip.exe"
) else (
    echo       Creating .venv...
    %PYTHON% -m venv .venv
    if errorlevel 1 (
        echo [ERROR] Failed to create venv
        pause
        exit /b 1
    )
    echo [OK] venv created
    set "PIP=.venv\Scripts\pip.exe"
)

REM ── Install missing dependencies ──────────────────────────────
echo.
echo [3/5] Installing dependencies...

.venv\Scripts\pip.exe install -r requirements.txt
if errorlevel 1 (
    echo.
    echo [ERROR] pip install failed
    pause
    exit /b 1
)


REM Check if llama-cpp-python installed after requirements
.venv\Scripts\python.exe -c "import llama_cpp; print('ok')" 2>nul
if errorlevel 1 (
    echo.
    echo       llama-cpp-python needs compilation. Running installer...
    echo       (Requires Visual Studio Build Tools - takes 5-10 min)
    echo.
    .venv\Scripts\python.exe install_llama.py
    if errorlevel 1 (
        echo.
        echo [ERROR] llama-cpp-python installation failed.
        echo       Install Visual Studio Build Tools manually:
        echo       https://visualstudio.microsoft.com/downloads/
        echo       Select "Desktop development with C++" workload.
        pause
        exit /b 1
    )
)

:after_install

REM ── Verify model ──────────────────────────────────────────────
echo.
echo [4/5] Checking model file...

set "PROJECT_MODEL=GayatriAI\models\gayatri\gemma-2-2b-it-IQ3_M.gguf"
set "RUNTIME_MODEL=%LOCALAPPDATA%\GayatriAI\models\gayatri\gemma-2-2b-it-IQ3_M.gguf"

if exist "%RUNTIME_MODEL%" (
    echo [OK] Model found in runtime location
) else if exist "%PROJECT_MODEL%" (
    echo [OK] Model found in project, copying to runtime...
    if not exist "%LOCALAPPDATA%\GayatriAI\models\gayatri" mkdir "%LOCALAPPDATA%\GayatriAI\models\gayatri"
    copy /Y "%PROJECT_MODEL%" "%RUNTIME_MODEL%" >nul
    echo [OK] Model copied
) else (
    echo [WARN] Model not found in either location.
    echo       Looked for: %PROJECT_MODEL%
    echo       Or place it at: %RUNTIME_MODEL%
    echo.
    echo       The app will launch but local model features won't work.
    echo       You can use cloud APIs ^(Anthropic, OpenAI, Google^) instead.
    echo.
    set /p CONTINUE="Continue anyway? (Y/N): "
    if /i not "%CONTINUE%"=="Y" exit /b 0
)

REM ── Launch ────────────────────────────────────────────────────
echo.
echo [5/5] Launching Gayatri AI...
echo.

.venv\Scripts\python.exe -m app.main
set "EXIT_CODE=%ERRORLEVEL%"

if %EXIT_CODE% neq 0 (
    echo.
    echo [ERROR] App exited with code %EXIT_CODE%.
    echo       Check %LOCALAPPDATA%\GayatriAI\logs\gayatri.log
    pause
)
