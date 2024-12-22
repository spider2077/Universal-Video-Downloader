@echo off
echo Building Universal Video Downloader executable...

:: Check for Python 3.12
python --version 2>&1 | findstr /C:"Python 3.12" >nul
if errorlevel 1 (
    echo Error: Python 3.12 is required but not found!
    echo Please install Python 3.12 from https://www.python.org/downloads/
    pause
    exit /b 1
)

:: Install PyInstaller if not already installed
python -m pip install pyinstaller

:: Create .ico file from PNG using temporary script
echo import PIL.Image > convert_icon.py
echo images = [] >> convert_icon.py
echo images.append(PIL.Image.open('icons/icon16.png')) >> convert_icon.py
echo images.append(PIL.Image.open('icons/icon48.png')) >> convert_icon.py
echo images.append(PIL.Image.open('icons/icon128.png')) >> convert_icon.py
echo images[0].save('app_icon.ico', format='ICO', sizes=[(16,16), (48,48), (128,128)]) >> convert_icon.py

:: Install Pillow for icon conversion
python -m pip install pillow

:: Convert icons to .ico
python convert_icon.py

:: Build the executable
pyinstaller --noconfirm --onefile ^
    --icon=app_icon.ico ^
    --name "Universal_Video_Downloader" ^
    --noconsole ^
    --clean ^
    --add-data "icons/icon16.png;icons" ^
    --add-data "icons/icon48.png;icons" ^
    --add-data "icons/icon128.png;icons" ^
    Downloader.py

:: Clean up temporary files
del convert_icon.py
del app_icon.ico
rmdir /s /q build
del Universal_Video_Downloader.spec

echo.
echo Build complete! Executable is in the dist folder.
echo.
pause 