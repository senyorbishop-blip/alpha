@echo off
title Casual DnD Server
cd /d "%~dp0"

echo.
echo  ============================================
echo   Casual DnD - Starting Server...
echo  ============================================
echo.
if "%DND_DATA_DIR%"=="" set "DND_DATA_DIR=%USERPROFILE%\Documents\CasualDnDData"

echo  Save data folder: %DND_DATA_DIR%

echo  Freeing port 8000...
for /f "tokens=5" %%a in ('netstat -aon 2^>nul ^| findstr ":8000 "') do (
    taskkill /PID %%a /F >nul 2>&1
)
timeout /t 1 /nobreak >nul

python --version >nul 2>&1
if %ERRORLEVEL% equ 0 (
    set PYTHON_CMD=python
) else (
    py --version >nul 2>&1
    if %ERRORLEVEL% equ 0 (
        set PYTHON_CMD=py
    ) else (
        echo  ERROR: Python not found. Install from https://python.org
        pause
        exit /b 1
    )
)

echo  Python executable:
%PYTHON_CMD% -c "import sys; print('  ' + sys.executable + '  (v' + sys.version.split()[0] + ')')"

echo  Installing dependencies...
%PYTHON_CMD% -m pip install -r requirements.txt --quiet
echo  Ready. Server starting at http://localhost:8000
echo  Keep this window open while playing.
echo  ============================================
echo.
%PYTHON_CMD% main.py

echo.
echo  ============================================
echo   SERVER STOPPED
echo  ============================================
echo.
pause
