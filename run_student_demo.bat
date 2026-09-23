@echo off
REM Redirect to canonical run.bat launcher
call "%~dp0run.bat"
exit /b %errorlevel%
