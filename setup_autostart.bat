@echo off
chcp 65001 >nul
echo ========================================
echo  PixAI - Setup Autostart on Login
echo ========================================
echo.

set SCRIPT_DIR=%~dp0
set PYTHON_PATH=%LOCALAPPDATA%\Programs\Python\Python310\python.exe
set MONITOR=%SCRIPT_DIR%monitor.py
set VBS=%SCRIPT_DIR%start_monitor.vbs
set LOG=%SCRIPT_DIR%logs\monitor_startup.log

:: Create VBS launcher (runs silently, no black cmd window)
(
echo Set WshShell = CreateObject^("WScript.Shell"^)
echo WshShell.Run "cmd /c """^& "%PYTHON_PATH%" ^& """ """^& "%MONITOR%" ^& """ >> """^& "%LOG%" ^& """ 2^>^&1", 0, False
) > "%VBS%"

:: Register with Task Scheduler: run on login, delay 1 min
schtasks /delete /tn "PixAI Monitor" /f >nul 2>&1
schtasks /create ^
  /tn "PixAI Monitor" ^
  /tr "wscript.exe \"%VBS%\"" ^
  /sc ONLOGON ^
  /delay 0001:00 ^
  /rl HIGHEST ^
  /f

if %errorlevel% equ 0 (
    echo.
    echo Setup complete!
    echo On every login, monitor.py will run automatically after 1 minute.
    echo It checks all accounts and claims any that haven't been claimed today.
    echo.
    echo Startup log: %LOG%
    echo State file:  %SCRIPT_DIR%state.json
) else (
    echo.
    echo ERROR: Setup failed. Please run this file as Administrator.
)
echo.
pause
