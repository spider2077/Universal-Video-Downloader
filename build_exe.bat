@echo off
REM Location: Universal-Video-Downloader/build_exe.bat
REM Script: build_exe.bat

echo Building Universal Video Downloader v2.1.0 executable...
echo.

cd /d "%~dp0"

:: Check Python
py --version >nul 2>&1
if errorlevel 1 (
    echo Error: Python not found! Install Python 3.12+ from https://www.python.org/downloads/
    exit /b 1
)

echo Installing build dependencies...
py -m pip install -U pip
py -m pip install -U pyinstaller pillow
py -m pip install -U -r requirements.txt

:: Regenerate the icon set (PNGs + .ico) from generate_icons.py
echo Generating application icons...
py generate_icons.py
copy /Y icons\app_icon.ico app_icon.ico >nul

echo.
echo Running PyInstaller...

:: Close running instances so exe can be overwritten
taskkill /F /IM Universal_Video_Downloader.exe >nul 2>&1

py -m PyInstaller --noconfirm --onefile ^
    --icon=app_icon.ico ^
    --add-data "icons\app_icon.ico;icons" ^
    --name "Universal_Video_Downloader" ^
    --noconsole ^
    --clean ^
    --hidden-import=yt_dlp ^
    --hidden-import=yt_dlp.networking.impersonate ^
    --hidden-import=curl_cffi ^
    --collect-all curl_cffi ^
    --collect-all customtkinter ^
    --collect-submodules yt_dlp ^
    Downloader.py

if errorlevel 1 (
    echo.
    echo Build FAILED!
    exit /b 1
)

:: Bundle config templates next to exe
if not exist dist\cookies mkdir dist\cookies
copy /Y settings.ini.example dist\settings.ini.example >nul
copy /Y cookies\template.txt dist\cookies\template.txt >nul

:: Clean up temporary build files
del app_icon.ico 2>nul
rmdir /s /q build 2>nul
del Universal_Video_Downloader.spec 2>nul

echo.
echo Build complete!
echo   dist\Universal_Video_Downloader.exe
echo   dist\settings.ini.example
echo   dist\cookies\template.txt
echo.
echo First run: copy settings.ini.example to settings.ini and add cookies to dist\cookies\
echo.
exit /b 0
