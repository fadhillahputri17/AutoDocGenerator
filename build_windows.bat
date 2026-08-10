@echo off
setlocal

cd /d "%~dp0"

echo ==========================================
echo AutoDocGenerator - Windows Build
echo ==========================================
echo.

if not exist ".venv\Scripts\python.exe" (
    echo ERROR: Virtual environment tidak ditemukan.
    echo Lokasi yang dicari:
    echo %CD%\.venv\Scripts\python.exe
    echo.
    pause
    exit /b 1
)

echo [1/5] Memeriksa PyInstaller...
".venv\Scripts\python.exe" -m PyInstaller --version

if errorlevel 1 (
    echo.
    echo ERROR: PyInstaller belum terpasang.
    echo Jalankan:
    echo .venv\Scripts\python.exe -m pip install pyinstaller
    echo.
    pause
    exit /b 1
)

echo.
echo [2/5] Menghapus hasil build lama...

if exist "build" (
    rmdir /s /q "build"
)

if exist "dist\AutoDocGenerator" (
    rmdir /s /q "dist\AutoDocGenerator"
)

echo.
echo [3/5] Menjalankan Ruff...

".venv\Scripts\python.exe" -m ruff check src tests launcher.py

if errorlevel 1 (
    echo.
    echo ERROR: Ruff menemukan masalah.
    echo Perbaiki terlebih dahulu sebelum build.
    echo.
    pause
    exit /b 1
)

echo.
echo [4/5] Menjalankan unit test...

".venv\Scripts\python.exe" -m pytest tests\unit -q

if errorlevel 1 (
    echo.
    echo ERROR: Unit test gagal.
    echo Build dibatalkan.
    echo.
    pause
    exit /b 1
)

echo.
echo [5/5] Membuat aplikasi Windows...

".venv\Scripts\python.exe" -m PyInstaller ^
    --clean ^
    --noconfirm ^
    "AutoDocGenerator.spec"

if errorlevel 1 (
    echo.
    echo ERROR: Build gagal.
    echo Periksa pesan PyInstaller di atas.
    echo.
    pause
    exit /b 1
)

echo.
echo ==========================================
echo BUILD BERHASIL
echo ==========================================
echo.
echo File aplikasi:
echo %CD%\dist\AutoDocGenerator\AutoDocGenerator.exe
echo.
echo Jangan memindahkan EXE sendirian.
echo Seluruh folder dist\AutoDocGenerator harus tetap bersama.
echo.

pause
endlocal