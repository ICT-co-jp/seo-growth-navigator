@echo off
REM ----------------------------------------------------------------------
REM ictgrowthhacker-mcp startup script (Windows)
REM Creates .venv if missing, installs dependencies, then starts server.
REM Run: .\run_server.bat
REM ----------------------------------------------------------------------

setlocal
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    echo [ictgrowthhacker-mcp] Creating .venv...
    py -3.11 -m venv .venv 2>NUL
    if errorlevel 1 (
        echo [ictgrowthhacker-mcp] py -3.11 not found, retrying with python
        python -m venv .venv
    )
)

call .venv\Scripts\activate.bat

REM Install/update dependencies (fast no-op if already installed)
".venv\Scripts\python.exe" -m pip install --quiet --upgrade pip
".venv\Scripts\python.exe" -m pip install --quiet -r requirements.txt

REM Start server
".venv\Scripts\python.exe" server.py
