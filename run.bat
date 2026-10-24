@echo off
setlocal EnableExtensions
cd /d "%~dp0"
title Generator Laporan

rem === JALUR CEPAT: Jika virtual environment dan dependensi sudah siap, langsung jalankan ===
if exist ".venv\Scripts\python.exe" if exist ".venv\.deps_ok" (
    set "PYTHONPATH=%~dp0src"
    if exist ".venv\Scripts\pythonw.exe" (
        start "" "%~dp0.venv\Scripts\pythonw.exe" -m generator.web.app
        exit /b 0
    )
    "%~dp0.venv\Scripts\python.exe" -m generator.web.app
    if errorlevel 1 pause
    exit /b 0
)

rem 1) Deteksi Python 3.12 (launcher py atau python di PATH)
set "PYTHON=py -3.12"
%PYTHON% -c "import sys" >nul 2>&1
if errorlevel 1 (
    set "PYTHON=python"
    python -c "import sys; sys.exit(0 if sys.version_info >= (3, 11) else 1)" >nul 2>&1
)
if errorlevel 1 (
    echo Python 3.12 tidak ditemukan.
    echo Pasang dari https://www.python.org/downloads/ dan centang "Add python.exe to PATH",
    echo lalu jalankan run.bat lagi.
    pause
    exit /b 1
)

rem 2) Buat virtual environment di folder aplikasi bila belum ada
if not exist ".venv\Scripts\python.exe" (
    echo [1/3] Membuat virtual environment .venv ...
    %PYTHON% -m venv .venv
    if errorlevel 1 (
        echo Gagal membuat virtual environment.
        pause
        exit /b 1
    )
)

set "VPY=%~dp0.venv\Scripts\python.exe"

rem 3) Pasang dependensi saat pertama kali, dengan pesan progres
if not exist ".venv\.deps_ok" (
    echo [2/3] Memasang dependensi dari requirements.txt ...
    echo       Paket besar: rapidocr untuk OCR dan onnxruntime untuk mesin ONNX.
    "%VPY%" -m pip install --upgrade pip
    "%VPY%" -m pip install -r requirements.txt
    if errorlevel 1 (
        echo Gagal memasang dependensi. Periksa koneksi internet lalu jalankan run.bat lagi.
        pause
        exit /b 1
    )
    type nul > ".venv\.deps_ok"
)

rem 4) Jalankan aplikasi Webview Desktop Modern
echo [3/3] Menjalankan Generator Laporan Modern ...
set "PYTHONPATH=%~dp0src"
if exist "%~dp0.venv\Scripts\pythonw.exe" (
    start "" "%~dp0.venv\Scripts\pythonw.exe" -m generator.web.app
    endlocal
    exit /b 0
)
"%VPY%" -m generator.web.app
if errorlevel 1 pause
endlocal
