@echo off
REM =========================================================================
REM  StAR - Build Windows executable
REM  Prerequisites: Python 3.9+ installed
REM =========================================================================

cd /d "%~dp0"

echo.
echo === StAR Windows Build ===
echo.

REM 0. Look for Python (make sure it really works, not the Microsoft Store stub)
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

REM Try common installation paths
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
echo Python found: %PYTHON%
%PYTHON% --version
echo.

REM 1. Install dependencies
echo [1/4] Installing dependencies...
%PYTHON% -m pip install --upgrade pip
%PYTHON% -m pip install numpy scipy matplotlib pandas scikit-image Pillow pyinstaller
if errorlevel 1 (
    echo ERROR: dependency installation failed.
    pause
    exit /b 1
)

REM 2. Stereology module (optional): requires pysizeunfolder from GitHub (needs git)
echo.
echo [2/4] Installing pysizeunfolder (Stereology module, optional)...
%PYTHON% -m pip install "git+https://github.com/thomasvdj/pysizeunfolder"
if errorlevel 1 (
    echo WARNING: pysizeunfolder not installed (Stereology module unavailable).
    echo          It requires git (https://git-scm.com/download/win^).
)

REM 3. Build with PyInstaller
echo.
echo [3/4] Building executable...
%PYTHON% -m PyInstaller StAR.spec --noconfirm
if errorlevel 1 (
    echo ERROR: build failed.
    pause
    exit /b 1
)

REM 4. Copy example data files
echo.
echo [4/4] Copying example data...
if exist "data" (
    xcopy /E /I /Y "data" "dist\StAR\data"
)

echo.
echo =========================================
echo  Build completed!
echo  The application is in: dist\StAR\
echo  Executable: dist\StAR\StAR.exe
echo =========================================
echo.
pause
