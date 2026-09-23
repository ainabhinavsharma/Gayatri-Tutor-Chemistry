@echo off
setlocal
cd /d "%~dp0"

REM Suppress console logs and launch Gayatri AI in pure GUI mode (no background command prompt)
set GAYATRI_LOG_LEVEL=WARNING

REM 1. Prefer virtual environment pythonw (pure silent GUI)
if exist "%~dp0.venv\Scripts\pythonw.exe" (
    start "" "%~dp0.venv\Scripts\pythonw.exe" -m app.main
    exit /b 0
)

REM 2. Check standalone compiled executable if present
if exist "%~dp0Gayatri_Chemistry_Tutor.exe" (
    start "" "%~dp0Gayatri_Chemistry_Tutor.exe"
    exit /b 0
)

REM 3. Check virtual environment python.exe
if exist "%~dp0.venv\Scripts\python.exe" (
    start "" "%~dp0.venv\Scripts\python.exe" -m app.main
    exit /b 0
)

REM 4. Check system pythonw.exe
where pythonw.exe >nul 2>&1
if %errorlevel% equ 0 (
    start "" pythonw.exe -m app.main
    exit /b 0
)

REM 5. Fallback to system python.exe
where python.exe >nul 2>&1
if %errorlevel% equ 0 (
    start "" python.exe -m app.main
    exit /b 0
)

echo [ERROR] Could not find Python environment or executable.
pause
exit /b 1
