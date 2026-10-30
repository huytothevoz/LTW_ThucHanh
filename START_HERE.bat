@echo off
setlocal
cd /d "%~dp0"
echo.
echo   CrawlInsight - one-click local setup and launch
echo   Starts XAMPP MariaDB automatically, prepares the database, then starts Laravel.
echo   Keep this window open while testing the application.
echo.
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\setup_windows.ps1"
if errorlevel 1 (
    echo Automatic setup failed. Read the error above and see README.md.
    pause
    exit /b 1
)
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\start_windows.ps1"
if errorlevel 1 echo Server stopped with an error. See README.md.
pause
