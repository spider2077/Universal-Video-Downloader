@echo off
REM Location: Universal-Video-Downloader/update_dependencies.bat
REM Script: update_dependencies.bat

echo Location: %~dp0
echo Script: update_dependencies.bat
echo.
echo Updating Python packages...
echo.

py -m pip install --upgrade pip
py -m pip install --upgrade "yt-dlp[default,curl-cffi]"
py -m pip install --upgrade requests
py -m pip install --upgrade selenium

echo.
echo Installed yt-dlp version:
py -c "import yt_dlp; print(yt_dlp.version.__version__)"

echo.
echo curl-cffi status:
py -c "import importlib.util; print('OK' if importlib.util.find_spec('curl_cffi') else 'MISSING - Facebook may fail')"

echo.
echo All dependencies updated!
pause
