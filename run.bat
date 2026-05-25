@echo off
:: ============================================================================
:: RUMI Scientist AI — Windows Launcher
:: ============================================================================
title RUMI Scientist AI

echo.
echo  ╔══════════════════════════════════════════════════════╗
echo  ║           RUMI Scientist AI  v1.0.0                 ║
echo  ║     Autonomous Cognitive AI for Research            ║
echo  ╚══════════════════════════════════════════════════════╝
echo.

:: Get the directory where this script is located
set "SCRIPT_DIR=%~dp0"
cd /d "%SCRIPT_DIR%"

:: --- Check Python ---
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python is not installed or not in PATH.
    echo         Install Python 3.12+ from https://python.org
    pause
    exit /b 1
)

:: --- Check if we're in a virtual environment ---
python -c "import sys; sys.exit(0 if hasattr(sys, 'real_prefix') or (sys.prefix != sys.base_prefix) else 1)" >nul 2>&1
if %errorlevel% neq 0 (
    echo [INFO] No virtual environment detected.
    echo        Consider creating one: python -m venv .venv ^&^& .venv\Scripts\activate
    echo.
)

:: --- Quick dependency check ---
echo [CHECK] Verifying dependencies...
python -c "import rich; import prompt_toolkit; import numpy; import requests" >nul 2>&1
if %errorlevel% neq 0 (
    echo [WARN] Some dependencies are missing. Installing...
    python -m pip install -r requirements.txt
    if %errorlevel% neq 0 (
        echo [ERROR] Failed to install dependencies.
        pause
        exit /b 1
    )
    echo [OK] Dependencies installed.
) else (
    echo [OK] Core dependencies found.
)
echo.

:: --- Launch RUMI ---
echo [LAUNCH] Starting RUMI Scientist AI...
echo.
python rumi_launcher.py
set "EXIT_CODE=%errorlevel%"
if %EXIT_CODE% neq 0 (
    echo [RUMI] Exited with code %EXIT_CODE%
)

:: --- On exit ---
echo.
echo [RUMI] Session ended.
pause
