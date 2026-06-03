@echo off
setlocal enabledelayedexpansion
:: ============================================================================
:: RUMI Scientist AI — Windows Launcher (v3)
:: Finds Python 3.13+ WITH rich + prompt_toolkit installed.
:: ============================================================================
title RUMI Scientist AI

echo.
echo  ╔══════════════════════════════════════════════════════╗
echo  ║           RUMI Scientist AI  v3.0.0                 ║
echo  ║     Autonomous Scientific Discovery Engine           ║
echo  ╚══════════════════════════════════════════════════════╝
echo.

set "SCRIPT_DIR=%~dp0"
cd /d "%SCRIPT_DIR%"

set "PYTHON_CMD="

:: 1) Check known paths FIRST (must have rich installed)
for %%P in (
    "%LOCALAPPDATA%\Programs\Python\Python313\python.exe"
    "%LOCALAPPDATA%\Programs\Python\Python312\python.exe"
    "%LOCALAPPDATA%\hermes\hermes-agent\venv\Scripts\python.exe"
) do (
    if exist %%P (
        %%P -c "import rich; import prompt_toolkit" >nul 2>&1
        if !errorlevel! equ 0 (
            set "PYTHON_CMD=%%~P"
            goto :found_python
        )
    )
)

:: 2) Check local venv
if exist ".venv\Scripts\python.exe" (
    .venv\Scripts\python.exe -c "import rich; import prompt_toolkit" >nul 2>&1
    if !errorlevel! equ 0 (
        set "PYTHON_CMD=.venv\Scripts\python.exe"
        goto :found_python
    )
)

:: 3) Last resort: PATH python (must have deps)
python -c "import rich; import prompt_toolkit" >nul 2>&1
if %errorlevel% equ 0 (
    set "PYTHON_CMD=python"
    goto :found_python
)

echo [ERROR] No Python with rich + prompt_toolkit found.
echo.
echo  Your default 'python' is msys64 which is missing dependencies.
echo  Install Python 3.13 from https://python.org then run this again,
echo  or create a venv:
echo    python3.13 -m venv .venv ^&^& .venv\Scripts\activate ^&^& pip install -r requirements.txt
echo.
pause
exit /b 1

:found_python
echo [OK] Using: %PYTHON_CMD%
%PYTHON_CMD% --version
echo.

:: --- Launch RUMI ---
if "%1"=="" (
    echo [LAUNCH] Starting RUMI Scientist AI...
    echo.
    %PYTHON_CMD% rumi_launcher.py
) else (
    echo [LAUNCH] Running discovery pipeline: %*
    echo.
    %PYTHON_CMD% run_discovery_v2.py %*
)

echo.
echo [RUMI] Session ended.
pause
