@echo off
REM ----------------------------------------------------------------------
REM ictgrowthhacker-mcp startup script (Windows)
REM Creates .venv if missing, installs locked dependencies, then starts server.
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

if not exist "requirements.lock" (
    echo [ictgrowthhacker-mcp] requirements.lock が見つかりません。
    exit /b 1
)

set "LOCK_HASH="
for /f "tokens=1" %%H in ('certutil -hashfile requirements.lock SHA256 ^| findstr /R "^[0-9A-Fa-f][0-9A-Fa-f]"') do (
    set "LOCK_HASH=%%H"
)
if not defined LOCK_HASH (
    echo [ictgrowthhacker-mcp] requirements.lock のハッシュ計算に失敗しました。
    exit /b 1
)

set "LOCK_MARKER=.venv\requirements.lock.sha256"
set "INSTALLED_HASH="
if exist "%LOCK_MARKER%" set /p INSTALLED_HASH=<"%LOCK_MARKER%"

if /I not "%INSTALLED_HASH%"=="%LOCK_HASH%" (
    echo [ictgrowthhacker-mcp] Installing locked dependencies...
    ".venv\Scripts\python.exe" -m pip install --quiet --no-deps -r requirements.lock
    if errorlevel 1 exit /b 1
    >"%LOCK_MARKER%" echo %LOCK_HASH%
)

REM Start server
".venv\Scripts\python.exe" server.py
