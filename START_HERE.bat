@echo off
setlocal
cd /d "%~dp0"
echo.
echo   CrawlInsight - safe local installation
echo   Does not modify XAMPP, MySQL, or other projects.
echo.
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\setup_windows.ps1"
if errorlevel 1 (
    echo Setup failed. Read the error above and see README.md.
    pause
    exit /b 1
)
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\start_windows.ps1"
if errorlevel 1 echo Server stopped with an error. See README.md.
pause
