@echo off
title OmniDoc Studio - Build
echo ================================================
echo   Build: OmniDoc Studio
echo ================================================
echo.

:: Check Python
python --version 2>nul || (echo [ERROR] Python not found. Install Python 3.10+. && pause && exit /b 1)

:: Install/upgrade requirements
echo [1/3] Installing Python dependencies...
pip install -r requirements.txt
if %ERRORLEVEL% neq 0 (echo [ERROR] pip install failed. && pause && exit /b 1)
echo [OK] Dependencies installed.
echo.

:: Install PyInstaller if missing
pip show pyinstaller >nul 2>&1 || pip install pyinstaller
echo [OK] PyInstaller ready.
echo.

:: Build the EXE
echo [2/3] Building executable (this may take 5-10 minutes)...
pyinstaller OmniDocStudio.spec --noconfirm
if %ERRORLEVEL% neq 0 (echo [ERROR] PyInstaller failed. & pause & exit /b 1)
echo [OK] EXE built.
echo.

echo [3/3] Done!
echo.
echo Output: dist\OmniDocStudio\\OmniDocStudio.exe
echo.
echo To run:   dist\OmniDocStudio\\OmniDocStudio.exe
echo.
pause
