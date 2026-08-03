@echo off
REM ============================================================
REM  AI Project Manager Assistant - one-click launcher
REM  Does the prework (dependency install) then starts the app.
REM  Requirement: Python 3.10+ must already be installed
REM  with "Add Python to PATH" checked.
REM ============================================================

cd /d "%~dp0"
title AI Project Manager Assistant

echo.
echo ==============================================
echo   AI Project Manager Assistant - starting up
echo ==============================================
echo.

REM --- 1. Find a working Python (prefer the "py" launcher) ---
set "PYCMD="
py -3 --version >nul 2>nul
if not errorlevel 1 (
    set "PYCMD=py -3"
) else (
    python --version >nul 2>nul
    if not errorlevel 1 set "PYCMD=python"
)

if not defined PYCMD (
    echo [ERROR] Python was not found on this PC.
    echo.
    echo Please install Python 3.10 or newer from:
    echo     https://www.python.org/downloads/
    echo Make sure to check "Add Python to PATH" during install,
    echo then run this file again.
    echo.
    pause
    exit /b 1
)

echo Using Python command: %PYCMD%

REM --- 2. Make sure dependencies are installed ---
echo Checking dependencies (streamlit, pandas)...
%PYCMD% -c "import streamlit, pandas" >nul 2>nul
if errorlevel 1 (
    echo Installing required packages, please wait...
    %PYCMD% -m pip install -r requirements.txt
    if errorlevel 1 (
        echo.
        echo [ERROR] Could not install the required packages.
        echo If you are on a corporate network, you may need a proxy, e.g.:
        echo     %PYCMD% -m pip install -r requirements.txt --proxy http://your-proxy:port
        echo.
        pause
        exit /b 1
    )
) else (
    echo Dependencies already installed.
)

REM --- 3. Launch the app ---
echo.
echo Starting the app... your browser will open at http://localhost:8501
echo Keep this window open while using the app. Press Ctrl+C here to stop it.
echo.
%PYCMD% -m streamlit run app.py

pause
