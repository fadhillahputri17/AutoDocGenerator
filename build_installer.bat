@echo off
setlocal

cd /d "%~dp0"

echo ==========================================
echo AutoDocGenerator - Build Installer
echo ==========================================
echo.

if not exist "dist\AutoDocGenerator\AutoDocGenerator.exe" (
    echo ERROR: Build aplikasi belum ditemukan.
    echo Jalankan build_windows.bat terlebih dahulu.
    echo.
    pause
    exit /b 1
)

set "ISCC=%LOCALAPPDATA%\Programs\Inno Setup 6\ISCC.exe"

if not exist "%ISCC%" (
    echo ERROR: Inno Setup Compiler tidak ditemukan di:
    echo "%ISCC%"
    echo.
    pause
    exit /b 1
)

if not exist "AutoDocGenerator.iss" (
    echo ERROR: File AutoDocGenerator.iss tidak ditemukan di:
    echo "%CD%"
    echo.
    pause
    exit /b 1
)

echo Compiler ditemukan:
echo "%ISCC%"
echo.

"%ISCC%" "AutoDocGenerator.iss"

if errorlevel 1 (
    echo.
    echo ERROR: Pembuatan installer gagal.
    pause
    exit /b 1
)

echo.
echo ==========================================
echo INSTALLER BERHASIL DIBUAT
echo ==========================================
echo Lokasi:
echo "%CD%\installer_output\AutoDocGenerator_Setup_0.1.0.exe"
echo.
pause
exit /b 0
