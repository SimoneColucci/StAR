@echo off
REM =========================================================================
REM  StAR - Quick GUI launcher (Windows)
REM  Double-click this file to start the application
REM =========================================================================

cd /d "%~dp0"

REM --- Look for Python (make sure it works, not the Microsoft Store stub) ---
set PYTHON=

py -3 --version >nul 2>&1
if not errorlevel 1 (
    set PYTHON=py -3
    goto :found
)

python --version >nul 2>&1
if not errorlevel 1 (
    set PYTHON=python
    goto :found
)

for %%P in (
    "%LOCALAPPDATA%\Programs\Python\Python313\python.exe"
    "%LOCALAPPDATA%\Programs\Python\Python312\python.exe"
    "%LOCALAPPDATA%\Programs\Python\Python311\python.exe"
    "%LOCALAPPDATA%\Programs\Python\Python310\python.exe"
    "%LOCALAPPDATA%\Programs\Python\Python39\python.exe"
    "C:\Python313\python.exe"
    "C:\Python312\python.exe"
    "C:\Python311\python.exe"
    "C:\Python310\python.exe"
    "C:\Python39\python.exe"
) do (
    if exist %%~P (
        %%~P --version >nul 2>&1
        if not errorlevel 1 (
            set "PYTHON=%%~P"
            goto :found
        )
    )
)

echo.
echo ================================================================
echo  ERROR: Python is not installed on this PC!
echo.
echo  1. Download Python from: https://www.python.org/downloads/
echo  2. Run the installer
echo  3. CHECK "Add Python to PATH" on the first screen
echo  4. Click "Install Now"
echo  5. Run this script again
echo.
echo  If Python is already installed but is not found,
echo  go to Settings - Apps - App execution aliases
echo  and DISABLE the "python.exe" and "python3.exe" aliases
echo ================================================================
echo.
pause
exit /b 1

:found

REM --- Check whether the dependencies are installed ---
%PYTHON% -c "import numpy, scipy, matplotlib, pandas, skimage, PIL" 2>nul
if errorlevel 1 (
    echo.
    echo Installing dependencies...
    echo.
    %PYTHON% -m pip install --upgrade pip
    %PYTHON% -m pip install -r requirements.txt
    if errorlevel 1 (
        echo.
        echo ERROR: dependency installation failed.
        echo.
        pause
        exit /b 1
    )
)

REM --- Optional dependency for the Stereology module (needs git) ---
REM Best-effort: a failure here does not stop the other three modules.
%PYTHON% -c "import pysizeunfolder" 2>nul
if errorlevel 1 (
    echo.
    echo Installing pysizeunfolder ^(Stereology module^)...
    %PYTHON% -m pip install "git+https://github.com/thomasvdj/pysizeunfolder"
    if errorlevel 1 (
        echo.
        echo WARNING: could not install "pysizeunfolder".
        echo          The Stereology tab will be unavailable.
        echo          It requires git ^(https://git-scm.com/download/win^).
        echo.
    )
)

echo Starting StAR...
%PYTHON% star_gui.py

if errorlevel 1 (
    echo.
    echo An error occurred. Check the messages above.
    pause
)
