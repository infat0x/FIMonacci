@echo off
echo Building FIMonacci APK...
echo.

cd /d %~dp0

echo Checking for Java...
java -version >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: Java is not installed or not in PATH
    echo Please install Java 17 or higher
    pause
    exit /b 1
)

echo.
echo Starting Gradle build...
echo This may take a few minutes on first run...
echo.

if exist gradlew.bat (
    call gradlew.bat assembleDebug
) else (
    echo ERROR: gradlew.bat not found
    echo Please run this script from the android directory
    pause
    exit /b 1
)

if %errorlevel% equ 0 (
    echo.
    echo ========================================
    echo BUILD SUCCESSFUL!
    echo ========================================
    echo.
    echo APK location:
    echo app\build\outputs\apk\debug\app-debug.apk
    echo.
    echo You can now transfer this APK to your phone and install it.
    echo.
) else (
    echo.
    echo ========================================
    echo BUILD FAILED
    echo ========================================
    echo.
    echo Please check the error messages above.
    echo.
)

pause

