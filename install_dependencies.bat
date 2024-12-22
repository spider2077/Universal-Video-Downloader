@echo off
echo Checking Python installation...

:: Check for Python 3.12 specifically
python --version 2>&1 | findstr /C:"Python 3.12" >nul
if errorlevel 1 (
    echo Error: Python 3.12 is required but not found!
    echo Please install Python 3.12 from https://www.python.org/downloads/
    pause
    exit /b 1
)

echo Python 3.12 found. Installing/Updating required packages...

:: Upgrade pip first
python -m pip install --upgrade pip

:: Install required packages
python -m pip install youtube-dl
python -m pip install requests
python -m pip install beautifulsoup4
python -m pip install selenium
python -m pip install tkinter

:: Check if installations were successful
python -c "import youtube_dl" 2>nul
if errorlevel 1 (
    echo Error installing youtube-dl
    pause
    exit /b 1
)

python -c "import requests" 2>nul
if errorlevel 1 (
    echo Error installing requests
    pause
    exit /b 1
)

python -c "import bs4" 2>nul
if errorlevel 1 (
    echo Error installing beautifulsoup4
    pause
    exit /b 1
)

python -c "import selenium" 2>nul
if errorlevel 1 (
    echo Error installing selenium
    pause
    exit /b 1
)

python -c "import tkinter" 2>nul
if errorlevel 1 (
    echo Error installing tkinter
    pause
    exit /b 1
)

echo.
echo All dependencies installed successfully!
echo You can now run the Video Downloader
pause