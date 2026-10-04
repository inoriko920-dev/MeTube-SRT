@echo off
setlocal
cd /d "%~dp0"
title MeTube-SRT - Mulai

echo ========================================
echo        MeTube-SRT - MULAI
echo ========================================
echo.

where docker >nul 2>&1
if errorlevel 1 (
  echo [GAGAL] Docker tidak ditemukan.
  echo Install dan jalankan Docker Desktop terlebih dahulu.
  pause
  exit /b 1
)

docker info >nul 2>&1
if errorlevel 1 (
  echo [GAGAL] Docker Desktop belum aktif.
  echo Jalankan Docker Desktop lalu coba lagi.
  pause
  exit /b 1
)

if not exist downloads mkdir downloads

set "METUBE_SRT_IMAGE_TAG=latest"
if exist VERSI_IMAGE.txt set /p METUBE_SRT_IMAGE_TAG=<VERSI_IMAGE.txt
if "%METUBE_SRT_IMAGE_TAG%"=="" set "METUBE_SRT_IMAGE_TAG=latest"

if /I "%METUBE_SRT_IMAGE_TAG%"=="local" goto LOCAL_BUILD

echo [1/3] Mencoba image GHCR versi %METUBE_SRT_IMAGE_TAG%...
docker pull ghcr.io/inoriko920-dev/metube-srt:%METUBE_SRT_IMAGE_TAG% >nul 2>&1
if errorlevel 1 goto LOCAL_BUILD

echo [2/3] Menyalakan MeTube-SRT versi %METUBE_SRT_IMAGE_TAG%...
docker compose -f docker-compose.release.yml up -d
if errorlevel 1 goto FAILED
set "MODE=release %METUBE_SRT_IMAGE_TAG%"
goto WAIT_APP

:LOCAL_BUILD
echo       Image rilis tidak tersedia atau mode lokal dipilih. Fallback ke build lokal.
echo [2/3] Build dan menyalakan dari source lokal...
docker compose up -d --build
if errorlevel 1 goto FAILED
set "MODE=local"

:WAIT_APP
echo [3/3] Menunggu aplikasi siap...
powershell -NoProfile -ExecutionPolicy Bypass -Command "$ok=$false; 1..45 ^| ForEach-Object { try { $r=Invoke-WebRequest -UseBasicParsing -Uri 'http://127.0.0.1:8081/' -TimeoutSec 2; if($r.StatusCode -eq 200){$ok=$true; break} } catch {}; Start-Sleep -Seconds 2 }; if(-not $ok){exit 1}"
if errorlevel 1 (
  echo [GAGAL] Container hidup tetapi web belum merespons.
  echo Jalankan: docker logs metube-srt
  pause
  exit /b 1
)

echo.
echo [SUKSES] MeTube-SRT aktif. Mode: %MODE%
echo Buka: http://localhost:8081
echo Folder hasil: %CD%\downloads
echo.
start "" "http://localhost:8081"
exit /b 0

:FAILED
echo.
echo [GAGAL] MeTube-SRT tidak dapat dijalankan.
echo Cek Docker Desktop dan log container.
pause
exit /b 1
