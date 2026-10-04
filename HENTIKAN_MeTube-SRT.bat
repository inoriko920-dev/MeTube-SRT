@echo off
setlocal
cd /d "%~dp0"
title MeTube-SRT - Hentikan

echo ========================================
echo      MeTube-SRT - HENTIKAN
echo ========================================
echo.

where docker >nul 2>&1
if errorlevel 1 (
  echo [GAGAL] Docker tidak ditemukan.
  pause
  exit /b 1
)

echo Menghentikan container MeTube-SRT...
docker rm -f metube-srt >nul 2>&1
if errorlevel 1 (
  echo Container MeTube-SRT tidak sedang berjalan.
) else (
  echo [SUKSES] MeTube-SRT sudah dihentikan.
)

echo File hasil download tetap aman di folder downloads.
pause
exit /b 0
