@echo off
:: ============================================================================
:: RUMI Scientist AI — Windows Launcher (v2)
:: Finds the correct Python 3.13+ with all dependencies installed.
:: ============================================================================
title RUMI Scientist AI

echo.
echo  ╔══════════════════════════════════════════════════════╗
echo  ║           RUMI Scientist AI  v2.0.0                 ║
echo  ║     Autonomous Scientific Discovery Engine           ║
echo  ╚══════════════════════════════════════════════════════╝
echo.

:: Get the directory where this script is located
set "SCRIPT_DIR=%~dp0"
cd /d "%SCRIPT_DIR%"

:: --- Find Python 3.13+ ---
:: Priority: 1) venv  2) PATH python  3) Common install locations
set "PYTHON_CMD="

:: Check if we're in a virtual environment
python -c "import sys; sys.exit(0 if sys.version_info >= (3, 11) else 1)" >nul 2>&1
if %errorlevel% equ 0 (
    set "PYTHON_CMD=python"
    goto :found_python
)

:: Try common Windows install locations
for %%P in (
    "%LOCALAPPDATA%\Programs\Python\Python313\python.exe"
    "%LOCALAPPDATA%\Programs\Python\Python312\python.exe"
    "%LOCALAPPDATA%\Programs\Python\Python311\python.exe"
    "C:\Python313\python.exe"
    "C:\Python312\python.exe"
    "C:\Python311\python.exe"
) do (
    if exist %%P (
        %%P -c "import sys; sys.exit(0 if sys.version_info >= (3, 11) else 1)" >nul 2>&1
        if !errorlevel! equ 0 (
            set "PYTHON_CMD=%%~P"
            goto :found_python
        )
    )
)

:: Last resort: try PATH python
python --version >nul 2>&1
if %errorlevel% equ 0 (
    set "PYTHON_CMD=python"
    goto :found_python
)

echo [ERROR] Python 3.11+ not found.
echo         Install from https://python.org or create a venv:
echo         python -m venv .venv ^&^& .venv\Scripts\activate ^&^& pip install -r requirements.txt
pause
exit /b 1

:found_python
echo [OK] Using: %PYTHON_CMD%
%PYTHON_CMD% --version
echo.

:: --- Quick dependency check ---
echo [CHECK] Verifying dependencies...
%PYTHON_CMD% -c "import rich; import groq; import google.genai" >nul 2>&1
if %errorlevel% neq 0 (
    echo [WARN] Some dependencies are missing. Installing...
    %PYTHON_CMD% -m pip install -r requirements.txt
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
if "%1"=="" (
    echo [LAUNCH] Starting RUMI Scientist AI (interactive mode)...
    echo.
    %PYTHON_CMD% rumi_launcher.py
) else (
    echo [LAUNCH] Running discovery pipeline: %*
    echo.
    %PYTHON_CMD% run_discovery_v2.py %*
)

set "EXIT_CODE=%errorlevel%"
if %EXIT_CODE% neq 0 (
    echo [RUMI] Exited with code %EXIT_CODE%
)

echo.
echo [RUMI] Session ended.
pause
