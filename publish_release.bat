@echo off
REM Location: Universal-Video-Downloader/publish_release.bat
REM Script: publish_release.bat
REM Publishes (or updates) the GitHub Release for the version below. Run build_exe.bat
REM and android\build_apk.bat first. Needs the GitHub CLI, logged in: gh auth login

set "VERSION=2.1.0"
set "REPO=spider2077/Universal-Video-Downloader"
set "ZIP=dist\Universal_Video_Downloader_v%VERSION%_Win64.zip"
set "NOTES=RELEASE_NOTES_v%VERSION%.md"

echo Publishing GitHub Release v%VERSION%...
echo.

cd /d "%~dp0"

where gh >nul 2>&1
if errorlevel 1 goto no_gh

gh auth status >nul 2>&1
if errorlevel 1 goto no_auth

if not exist "dist\Universal_Video_Downloader.exe" goto no_exe
if not exist "%NOTES%" goto no_notes

set "ASSETS=dist\Universal_Video_Downloader.exe"
if exist "dist\Universal_Video_Downloader.apk" (
    set "ASSETS=%ASSETS% dist\Universal_Video_Downloader.apk"
) else (
    echo Note: dist\Universal_Video_Downloader.apk not found - releasing without the Android app.
)

echo Creating release zip...
powershell -NoProfile -Command "Compress-Archive -Force -Path 'dist\Universal_Video_Downloader.exe','dist\settings.ini.example','dist\cookies\template.txt' -DestinationPath '%ZIP%'"
if errorlevel 1 goto zip_failed
set "ASSETS=%ASSETS% %ZIP%"

gh release view v%VERSION% --repo %REPO% >nul 2>&1
if errorlevel 1 goto create_release
goto upload_release

:create_release
gh release create v%VERSION% --repo %REPO% --title "Universal Video Downloader v%VERSION%" --notes-file "%NOTES%" %ASSETS%
goto done

:upload_release
echo Release v%VERSION% exists. Updating assets...
gh release upload v%VERSION% --repo %REPO% --clobber %ASSETS%
goto done

:no_gh
echo Error: GitHub CLI not found. Install from https://cli.github.com/
exit /b 1

:no_auth
echo Please log in first: gh auth login
exit /b 1

:no_exe
echo Error: Run build_exe.bat first.
exit /b 1

:no_notes
echo Error: %NOTES% not found.
exit /b 1

:zip_failed
echo Error: could not create %ZIP%.
exit /b 1

:done
if errorlevel 1 (
    echo Release publish FAILED.
    exit /b 1
)
echo.
echo Release: https://github.com/%REPO%/releases/tag/v%VERSION%
echo.
exit /b 0
