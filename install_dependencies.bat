@echo off
echo Checking Python installation...

python --version >nul 2>&1
if errorlevel 1 (
    echo Python is not installed or not in PATH!
    echo Please install Python from https://www.python.org/downloads/
    echo Make sure to check "Add Python to PATH" during installation
    pause
    exit /b 1
)

echo Installing dependencies...
python -m pip install --upgrade pip
pip install yt-dlp requests beautifulsoup4 selenium

if errorlevel 1 (
    echo Error installing dependencies!
    pause
    exit /b 1
)

echo.
echo Dependencies installed successfully!
echo.
pause