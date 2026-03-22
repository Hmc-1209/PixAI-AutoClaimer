@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo ========================================
echo  PixAI Auto Claim - Manual Run
echo ========================================
echo.
python monitor.py
echo.
pause
