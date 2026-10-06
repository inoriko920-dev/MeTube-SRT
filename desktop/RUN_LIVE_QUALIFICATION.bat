@echo off
setlocal
cd /d "%~dp0"
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\run_live_qualification_windows.ps1" -InstallMissingTools
set "EXIT_CODE=%ERRORLEVEL%"
echo.
if not "%EXIT_CODE%"=="0" echo Qualification did not pass. Keep the evidence ZIP for review.
pause
exit /b %EXIT_CODE%
