@echo off
title Library Space Management Tool Setup & Launch

echo.
echo ===================================================
echo   Welcome to the Library Space Management Tool!
echo ===================================================
echo.
echo This script will:
echo 1. Install necessary components (Streamlit, Pandas, Plotly).
echo 2. Launch the tool in your web browser.
echo.
echo Please ensure you have Python 3.8 or newer installed.
echo.

pause

echo.
echo --- Step 1: Installing required libraries ---
echo    (This may take a few moments and requires an internet connection)
echo.

REM Check if Python is in PATH
where python >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: Python was not found in your system's PATH.
    echo Please ensure Python is installed and "Add Python to PATH" was checked during installation.
    echo You may need to restart your computer after installing Python.
    echo.
    pause
    exit /b 1
)

REM Use py.exe launcher if available, otherwise python.exe
where py >nul 2>&1
if %errorlevel% equ 0 (
    set PYTHON_EXE=py
) else (
    set PYTHON_EXE=python
)

"%PYTHON_EXE%" -m pip install streamlit pandas plotly --upgrade

if %errorlevel% neq 0 (
    echo.
    echo ERROR: Failed to install required libraries.
    echo Please check your internet connection or try running this script again.
    echo If the issue persists, you might need administrator privileges.
    echo.
    pause
    exit /b 1
)

echo.
echo Libraries installed successfully!
echo.

echo --- Step 2: Launching the Library Space Management Tool ---
echo    (This will open in your default web browser)
echo.

REM Check if library_app.py exists in the same directory
if not exist "library_app.py" (
    echo ERROR: 'library_app.py' not found in this folder.
    echo Please make sure 'library_app.py' is in the same directory as this script.
    echo.
    pause
    exit /b 1
)

"%PYTHON_EXE%" -m streamlit run "library_app.py"

echo.
echo If the tool did not open automatically, please open your web browser
echo and go to: http://localhost:8501
echo.
echo The tool is now running. Close this window to stop the tool.
echo.
pause