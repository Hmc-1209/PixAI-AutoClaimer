@echo off
chcp 65001 >nul
echo ========================================
echo  PixAI - Setup Autostart on Login
echo ========================================
echo.

set PYTHONW=C:\Users\danny\AppData\Local\Programs\Python\Python310\pythonw.exe
set MONITOR=D:\PixAI-AutoClaimer\monitor.py

:: Delete old task and VBS if they exist
schtasks /delete /tn "PixAI Monitor" /f >nul 2>&1
del /f /q "D:\PixAI-AutoClaimer\start_monitor.vbs" >nul 2>&1

:: Register task: run pythonw.exe directly (no console window)
schtasks /create ^
  /tn "PixAI Monitor" ^
  /tr "\"%PYTHONW%\" \"%MONITOR%\"" ^
  /sc ONLOGON ^
  /delay 0001:00 ^
  /rl HIGHEST ^
  /f

if %errorlevel% equ 0 (
    echo.
    echo Setup complete!
    echo On every login, monitor.py will run silently after 1 minute.
    echo.
    echo Log: D:\PixAI-AutoClaimer\logs\YYYY-MM.log
    echo State: D:\PixAI-AutoClaimer\state.json
) else (
    echo.
    echo ERROR: Setup failed. Please run as Administrator.
)
echo.
pause
