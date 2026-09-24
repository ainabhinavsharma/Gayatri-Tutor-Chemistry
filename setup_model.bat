@echo off
title Gayatri Chemistry Tutor — Model Setup
cd /d "%~dp0"
echo.
echo ============================================================
echo   GAYATRI CHEMISTRY TUTOR — Model Setup
echo ============================================================
echo.

set "MODEL_DIR=%~dp0models\gayatri"
set "MODEL_FILE=%MODEL_DIR%\Gayatri-Tutor-SLM-Q4_K_M.gguf"
set "DOWNLOADS=%USERPROFILE%\Downloads\Gayatri-Tutor-SLM-Q4_K_M.gguf"

REM Create model directory if it doesn't exist
if not exist "%MODEL_DIR%" mkdir "%MODEL_DIR%"

REM Check if model already installed
if exist "%MODEL_FILE%" (
    echo [OK] Model already installed:
    echo      %MODEL_FILE%
    echo.
    echo Ready to launch! Double-click Gayatri_Chemistry_Tutor.exe
    pause
    exit /b 0
)

REM Check Downloads folder
if exist "%DOWNLOADS%" (
    echo [FOUND] Model found in Downloads folder.
    echo         Copying to application directory...
    copy "%DOWNLOADS%" "%MODEL_FILE%"
    if errorlevel 1 (
        echo [ERROR] Copy failed. Please manually copy:
        echo         From: %DOWNLOADS%
        echo         To:   %MODEL_FILE%
        pause
        exit /b 1
    )
    echo [OK] Model installed successfully!
    echo.
    echo Ready to launch! Double-click Gayatri_Chemistry_Tutor.exe
    pause
    exit /b 0
)

REM Model not found — show instructions
echo [INFO] Model file not found. Please complete setup:
echo.
echo  1. Download the model file (379 MB) from:
echo     https://github.com/Gayatri-Education/Gayatri-Tutor-ChemistryDemo/releases/latest
echo     File: Gayatri-Tutor-SLM-Q4_K_M.gguf
echo.
echo  2. Place the downloaded file here:
echo     %MODEL_FILE%
echo.
echo  3. Run this script again, OR simply launch the app.
echo     The app will show a helpful message if the model is missing.
echo.
echo ============================================================
pause
exit /b 0
