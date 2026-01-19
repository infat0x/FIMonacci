@echo off
echo.
echo  ============================================================
echo   FIMonacci Agent - Build Script
echo  ============================================================
echo.

REM Check if Python is available
python --version >nul 2>&1
if errorlevel 1 (
    echo  ERROR: Python is not installed or not in PATH
    pause
    exit /b 1
)

REM Install dependencies
echo  [1/4] Installing dependencies...
pip install -r requirements.txt -q
pip install pillow pyinstaller -q

REM Check for logo and create icon
echo  [2/4] Processing icon...
if exist "logo.png" (
    python create_icon.py
) else if exist "logo.jpg" (
    python create_icon.py
) else if not exist "icon.ico" (
    echo  WARNING: No logo.png found. Build will use default icon.
    echo  Place logo.png in this folder and rebuild for custom icon.
)

REM Run build script
echo.
echo  [3/4] Building executable...
python build.py

echo.
echo  [4/4] Done!
echo.
pause

