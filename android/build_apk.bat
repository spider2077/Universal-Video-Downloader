@echo off
REM Location: Universal-Video-Downloader/android/build_apk.bat
REM Script: build_apk.bat

echo Building Universal Video Downloader for Android (debug APK)...
echo.

cd /d "%~dp0"

:: Gradle needs a JDK 17+. Android Studio ships one; use it when JAVA_HOME is not set.
if not defined JAVA_HOME (
    if exist "%ProgramFiles%\Android\Android Studio\jbr\bin\java.exe" (
        set "JAVA_HOME=%ProgramFiles%\Android\Android Studio\jbr"
    )
)
if not defined JAVA_HOME (
    echo Error: JAVA_HOME is not set and Android Studio was not found.
    echo Install Android Studio from https://developer.android.com/studio
    exit /b 1
)

:: local.properties points Gradle at the Android SDK; it is machine-specific and git-ignored.
:: Forward slashes: a backslash is an escape character in .properties files.
set "SDK_DIR=%LOCALAPPDATA%\Android\Sdk"
set "SDK_DIR=%SDK_DIR:\=/%"
if not exist local.properties (
    if exist "%LOCALAPPDATA%\Android\Sdk" (
        >local.properties echo sdk.dir=%SDK_DIR%
    ) else (
        echo Error: Android SDK not found. Open this folder once in Android Studio.
        exit /b 1
    )
)

call "%~dp0gradlew.bat" --console=plain testDebugUnitTest assembleDebug
if errorlevel 1 (
    echo.
    echo Build FAILED!
    exit /b 1
)

if not exist ..\dist mkdir ..\dist
copy /Y app\build\outputs\apk\debug\app-debug.apk ..\dist\Universal_Video_Downloader.apk >nul

echo.
echo Build complete!
echo   dist\Universal_Video_Downloader.apk
echo.
echo Install over USB:  adb install -r dist\Universal_Video_Downloader.apk
echo Or copy the APK to the phone and open it (allow "install unknown apps").
echo.
exit /b 0
