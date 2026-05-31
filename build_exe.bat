@echo off
REM Location: Universal-Video-Downloader/build_exe.bat
REM Script: build_exe.bat

echo Building Universal Video Downloader v2.0.2 executable...
echo.

cd /d "%~dp0"

:: Check Python
py --version >nul 2>&1
if errorlevel 1 (
    echo Error: Python not found! Install Python 3.12+ from https://www.python.org/downloads/
    pause
    exit /b 1
)

echo Installing build dependencies...
py -m pip install -U pip
py -m pip install -U pyinstaller pillow
py -m pip install -U -r requirements.txt

:: Generate icons if missing
if not exist icons\icon16.png (
    echo Generating application icons...
    py generate_icons.py
)

:: Create .ico from PNG icons
echo from PIL import Image > convert_icon.py
echo i16 = Image.open('icons/icon16.png') >> convert_icon.py
echo i48 = Image.open('icons/icon48.png') >> convert_icon.py
echo i128 = Image.open('icons/icon128.png') >> convert_icon.py
echo i16.save('app_icon.ico', format='ICO', sizes=[(16,16), (48,48), (128,128)]) >> convert_icon.py
py convert_icon.py

echo.
echo Running PyInstaller...

:: Close running instances so exe can be overwritten
taskkill /F /IM Universal_Video_Downloader.exe >nul 2>&1

py -m PyInstaller --noconfirm --onefile ^
    --icon=app_icon.ico ^
    --name "Universal_Video_Downloader" ^
    --noconsole ^
    --clean ^
    --hidden-import=yt_dlp ^
    --hidden-import=yt_dlp.networking.impersonate ^
    --hidden-import=curl_cffi ^
    --collect-all curl_cffi ^
    --collect-submodules yt_dlp ^
    Downloader.py

if errorlevel 1 (
    echo.
    echo Build FAILED!
    pause
    exit /b 1
)

:: Bundle config templates next to exe
if not exist dist\cookies mkdir dist\cookies
copy /Y settings.ini.example dist\settings.ini.example >nul
copy /Y cookies\template.txt dist\cookies\template.txt >nul

:: Clean up temporary build files
del convert_icon.py 2>nul
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
pause
