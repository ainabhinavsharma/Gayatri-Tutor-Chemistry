@echo off
setlocal
cd /d "%~dp0"

REM Suppress console logs and launch Gayatri AI in pure GUI mode (no background command prompt)
set GAYATRI_LOG_LEVEL=WARNING

if exist "%~dp0.venv\Scripts\pythonw.exe" (
    start "" "%~dp0.venv\Scripts\pythonw.exe" -m app.main
    exit /b 0
)

if exist "%~dp0.venv\Scripts\python.exe" (
    start "" "%~dp0.venv\Scripts\python.exe" -m app.main
    exit /b 0
)

if exist "%~dp0Gayatri_Chemistry_Tutor.exe" (
    start "" "%~dp0Gayatri_Chemistry_Tutor.exe"
    exit /b 0
)

echo [ERROR] Could not find Python environment or executable.
pause
exit /b 1
