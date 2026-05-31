@echo off
REM Location: Universal-Video-Downloader/install_dependencies.bat
REM Script: install_dependencies.bat

echo Installing Python dependencies...
py -m pip install -U pip
py -m pip install -r requirements.txt

echo.
echo Checking for FFmpeg...
where ffmpeg >nul 2>nul
if %errorlevel% neq 0 (
    echo FFmpeg not found. Please install FFmpeg:
    echo 1. Download from https://ffmpeg.org/download.html
    echo 2. Extract and add the bin folder to PATH
    echo 3. Restart this script
    exit /b 1
) else (
    echo FFmpeg is installed.
)

echo.
echo Creating necessary directories...
if not exist cookies mkdir cookies
if not exist Output mkdir Output
if not exist settings.ini (
    copy settings.ini.example settings.ini >nul
    echo Created settings.ini from settings.ini.example
)

echo.
echo Installation complete!
echo.
echo Requirements:
echo   - Python 3.12 or higher
echo   - FFmpeg on PATH
echo   - cookies/ folder for Facebook, Instagram, etc.
echo.
echo Run: run_downloader.bat
exit /b 0
