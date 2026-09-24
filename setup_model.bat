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

REM Search common candidate paths
set "SRC="
if exist "%USERPROFILE%\Downloads\Gayatri-Tutor-SLM-Q4_K_M.gguf" set "SRC=%USERPROFILE%\Downloads\Gayatri-Tutor-SLM-Q4_K_M.gguf"
if not defined SRC if exist "%USERPROFILE%\Desktop\gayatri\Gayatri Chem Tutor\release_staging\Gayatri-Tutor-SLM-Q4_K_M.gguf" set "SRC=%USERPROFILE%\Desktop\gayatri\Gayatri Chem Tutor\release_staging\Gayatri-Tutor-SLM-Q4_K_M.gguf"
if not defined SRC if exist "%USERPROFILE%\Desktop\gayatri\Gayatri Chem Tutor\GayatriAI\models\gayatri\Gayatri-Tutor-SLM-Q4_K_M.gguf" set "SRC=%USERPROFILE%\Desktop\gayatri\Gayatri Chem Tutor\GayatriAI\models\gayatri\Gayatri-Tutor-SLM-Q4_K_M.gguf"
if not defined SRC if exist "%USERPROFILE%\Desktop\gayatri\test_portable_v301\models\gayatri\Gayatri-Tutor-SLM-Q4_K_M.gguf" set "SRC=%USERPROFILE%\Desktop\gayatri\test_portable_v301\models\gayatri\Gayatri-Tutor-SLM-Q4_K_M.gguf"

if defined SRC (
    echo [FOUND] Model detected at:
    echo         %SRC%
    echo         Installing to application directory...
    copy "%SRC%" "%MODEL_FILE%"
    if errorlevel 1 (
        echo [ERROR] Copy failed. Please manually copy:
        echo         From: %SRC%
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
echo  3. Launch the app (or run this script to verify).
echo.
echo ============================================================
pause
exit /b 0
