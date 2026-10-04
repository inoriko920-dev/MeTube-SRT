@echo off
setlocal
cd /d "%~dp0"
title MeTube-SRT - Update

echo ========================================
echo        MeTube-SRT - UPDATE
echo ========================================
echo.

where docker >nul 2>&1
if errorlevel 1 (
  echo [GAGAL] Docker tidak ditemukan.
  pause
  exit /b 1
)

docker info >nul 2>&1
if errorlevel 1 (
  echo [GAGAL] Docker Desktop belum aktif.
  pause
  exit /b 1
)

set "LATEST_TAG="
echo [1/4] Mencari release stabil terbaru di GitHub...
for /f "usebackq delims=" %%V in (`powershell -NoProfile -ExecutionPolicy Bypass -Command "$ErrorActionPreference='Stop'; $r=Invoke-RestMethod -Headers @{'User-Agent'='MeTube-SRT-Windows'} -Uri 'https://api.github.com/repos/inoriko920-dev/MeTube-SRT/releases/latest'; [Console]::Write($r.tag_name)" 2^>nul`) do set "LATEST_TAG=%%V"

if "%LATEST_TAG%"=="" (
  echo       Tidak bisa membaca release terbaru. Mencoba update source lokal...
  goto LOCAL_UPDATE
)

echo       Release stabil terbaru: %LATEST_TAG%
echo [2/4] Mengambil image %LATEST_TAG%...
docker pull ghcr.io/inoriko920-dev/metube-srt:%LATEST_TAG%
if errorlevel 1 goto LOCAL_UPDATE

set "METUBE_SRT_IMAGE_TAG=%LATEST_TAG%"
echo [3/4] Mengganti container ke %LATEST_TAG%...
docker rm -f metube-srt >nul 2>&1
docker compose -f docker-compose.release.yml up -d
if errorlevel 1 goto FAILED

>VERSI_IMAGE.txt echo %LATEST_TAG%
set "MODE=release %LATEST_TAG%"
goto WAIT_APP

:LOCAL_UPDATE
echo.
echo       Release GHCR tidak dapat dipakai. Mencoba update source lokal...
where git >nul 2>&1
if errorlevel 1 (
  echo [GAGAL] Update release gagal dan Git tidak ditemukan untuk fallback source lokal.
  pause
  exit /b 1
)

echo [2/4] Menarik source terbaru dari GitHub...
git pull --ff-only
if errorlevel 1 (
  echo [GAGAL] git pull gagal. Ada perubahan lokal atau koneksi bermasalah.
  pause
  exit /b 1
)

echo [3/4] Build ulang dari source terbaru...
docker compose up -d --build
if errorlevel 1 goto FAILED
>VERSI_IMAGE.txt echo local
set "MODE=local"

:WAIT_APP
echo [4/4] Memastikan aplikasi siap...
powershell -NoProfile -ExecutionPolicy Bypass -Command "$ok=$false; 1..45 ^| ForEach-Object { try { $r=Invoke-WebRequest -UseBasicParsing -Uri 'http://127.0.0.1:8081/' -TimeoutSec 2; if($r.StatusCode -eq 200){$ok=$true; break} } catch {}; Start-Sleep -Seconds 2 }; if(-not $ok){exit 1}"
if errorlevel 1 goto FAILED

echo.
echo [SUKSES] MeTube-SRT sudah diperbarui. Mode: %MODE%
echo File di folder downloads tetap dipertahankan.
start "" "http://localhost:8081"
pause
exit /b 0

:FAILED
echo.
echo [GAGAL] Proses update tidak selesai.
echo Cek Docker Desktop dan jalankan docker logs metube-srt bila perlu.
pause
exit /b 1
