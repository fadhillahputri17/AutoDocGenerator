@echo off
setlocal

cd /d "%~dp0"

echo ==========================================
echo AutoDocGenerator - Full Release Build
echo ==========================================
echo.

if not exist ".venv\Scripts\python.exe" (
    echo ERROR: Virtual environment .venv tidak ditemukan.
    echo.
    pause
    exit /b 1
)

call ".venv\Scripts\activate.bat"

echo [1/4] Menjalankan Ruff...
ruff check src tests launcher.py
if errorlevel 1 (
    echo.
    echo ERROR: Ruff gagal.
    pause
    exit /b 1
)

echo.
echo [2/4] Menjalankan test...
pytest -q
if errorlevel 1 (
    echo.
    echo ERROR: Test gagal.
    pause
    exit /b 1
)

echo.
echo [3/4] Membuat build Windows...
call build_windows.bat
if errorlevel 1 (
    echo.
    echo ERROR: Build Windows gagal.
    pause
    exit /b 1
)

echo.
echo [4/4] Membuat installer...
call build_installer.bat
if errorlevel 1 (
    echo.
    echo ERROR: Build installer gagal.
    pause
    exit /b 1
)

echo.
echo ==========================================
echo RELEASE SELESAI
echo ==========================================
echo Installer:
echo %CD%\installer_output\AutoDocGenerator_Setup_0.1.0.exe
echo.
pause
exit /b 0
