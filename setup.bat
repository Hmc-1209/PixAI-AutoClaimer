@echo off
chcp 65001 >nul
echo ========================================
echo  PixAI Claimer - First-time Setup
echo ========================================
echo.

echo [1/3] Installing Python packages...
pip install pydoll-python schedule
if %errorlevel% neq 0 (
    echo ERROR: pip install failed. Make sure Python is installed.
    pause
    exit /b 1
)

echo.
echo [2/3] Downloading Chromium browser...
patchright install chromium
if %errorlevel% neq 0 (
    echo ERROR: Chromium install failed.
    pause
    exit /b 1
)

echo.
echo [3/3] Done!
echo.
echo Copy accounts.example.json to accounts.json and fill in your credentials.
echo Then double-click run_claim.bat to run manually, or setup_autostart.bat to run on login.
echo.
pause
