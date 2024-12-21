@echo off
echo Starting Video Downloader...

:: Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo Error: Python is not installed or not in PATH!
    echo Please run install_dependencies.bat first
    pause
    exit /b 1
)

:: Check if Downloader.py exists
if not exist "Downloader.py" (
    echo Error: Downloader.py not found!
    echo Make sure this batch file is in the same directory as Downloader.py
    pause
    exit /b 1
)

:: Run the script and exit immediately if successful
start /b pythonw Downloader.py
if errorlevel 1 (
    echo.
    echo Error occurred while running the downloader!
    pause
) else (
    exit
)
pause 