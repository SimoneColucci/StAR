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
set "PYTHON_EXE="
set "PYTHON_ARGS="

py -3 --version >nul 2>&1
if not errorlevel 1 goto :found_py

python --version >nul 2>&1
if not errorlevel 1 goto :found_python

goto :python_missing

:found_py
set "PYTHON_EXE=py"
set "PYTHON_ARGS=-3"
goto :found

:found_python
set "PYTHON_EXE=python"
goto :found

:python_missing
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
echo Python found: %PYTHON_EXE% %PYTHON_ARGS%
"%PYTHON_EXE%" %PYTHON_ARGS% --version
echo.

REM 1. Install dependencies
echo [1/4] Installing dependencies...
call "%PYTHON_EXE%" %PYTHON_ARGS% -m pip install --upgrade pip
call "%PYTHON_EXE%" %PYTHON_ARGS% -m pip install numpy scipy matplotlib pandas scikit-image Pillow pyinstaller
if errorlevel 1 goto :dependency_error

REM 2. Stereology module (optional): requires pysizeunfolder from GitHub (needs git)
echo.
echo [2/4] Installing pysizeunfolder (Stereology module, optional)...
call "%PYTHON_EXE%" %PYTHON_ARGS% -m pip install "git+https://github.com/thomasvdj/pysizeunfolder"
if errorlevel 1 echo WARNING: pysizeunfolder not installed (Stereology module unavailable).
if errorlevel 1 echo          It requires git (https://git-scm.com/download/win^).

REM 3. Build with PyInstaller
echo.
echo [3/4] Building executable...
call "%PYTHON_EXE%" %PYTHON_ARGS% -m PyInstaller StAR.spec --noconfirm --distpath dist_windows
if errorlevel 1 goto :build_error

REM 4. Copy example data files
echo.
echo [4/4] Copying example data...
if exist "data" xcopy /E /I /Y "data" "dist_windows\StAR\data"

if not exist "dist_windows\StAR\StAR.exe" goto :output_error

echo.
echo =========================================
echo  Build completed!
echo  The application is in: dist_windows\StAR\
echo  Executable: dist_windows\StAR\StAR.exe
echo =========================================
echo.
pause
exit /b 0

:dependency_error
echo ERROR: dependency installation failed.
pause
exit /b 1

:build_error
echo ERROR: build failed.
pause
exit /b 1

:output_error
echo ERROR: PyInstaller completed but the executable was not found.
pause
exit /b 1
