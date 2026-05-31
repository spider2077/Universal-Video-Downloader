@echo off
REM Location: Universal-Video-Downloader/publish_release.bat
REM Script: publish_release.bat

echo Publishing GitHub Release v2.0.3...
echo.

cd /d "%~dp0"

where gh >nul 2>&1
if errorlevel 1 goto no_gh

gh auth status >nul 2>&1
if errorlevel 1 goto no_auth

if not exist "dist\Universal_Video_Downloader.exe" goto no_exe

if not exist "dist\Universal_Video_Downloader_v2.0.3_Win64.zip" (
    echo Creating release zip...
    powershell -NoProfile -Command "Compress-Archive -Force -Path 'dist\Universal_Video_Downloader.exe','dist\settings.ini.example','dist\cookies\template.txt' -DestinationPath 'dist\Universal_Video_Downloader_v2.0.3_Win64.zip'"
)

gh release view v2.0.3 >nul 2>&1
if errorlevel 1 goto create_release
goto upload_release

:create_release
gh release create v2.0.3 --repo spider2077/Universal-Video-Downloader --title "Universal Video Downloader v2.0.3" --notes-file RELEASE_NOTES_v2.0.3.md "dist\Universal_Video_Downloader.exe" "dist\Universal_Video_Downloader_v2.0.3_Win64.zip"
goto done

:upload_release
echo Release v2.0.3 exists. Updating assets...
gh release upload v2.0.3 --repo spider2077/Universal-Video-Downloader --clobber "dist\Universal_Video_Downloader.exe" "dist\Universal_Video_Downloader_v2.0.3_Win64.zip"
goto done

:no_gh
echo Error: GitHub CLI not found. Install from https://cli.github.com/
pause
exit /b 1

:no_auth
echo Please log in first: gh auth login
pause
exit /b 1

:no_exe
echo Error: Run build_exe.bat first.
pause
exit /b 1

:done
if errorlevel 1 (
    echo Release publish FAILED.
    pause
    exit /b 1
)
echo.
echo Release: https://github.com/spider2077/Universal-Video-Downloader/releases/tag/v2.0.3
echo.
pause
