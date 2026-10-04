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

echo [1/3] Mengambil image rilis terbaru...
docker pull ghcr.io/inoriko920-dev/metube-srt:latest
if errorlevel 1 goto LOCAL_UPDATE

echo [2/3] Mengganti container ke image terbaru...
docker rm -f metube-srt >nul 2>&1
docker compose -f docker-compose.release.yml up -d
if errorlevel 1 goto FAILED
set "MODE=release"
goto DONE

:LOCAL_UPDATE
echo       GHCR tidak bisa dipull. Mencoba update source lokal...
where git >nul 2>&1
if errorlevel 1 (
  echo [GAGAL] GHCR tidak tersedia dan Git tidak ditemukan untuk fallback source lokal.
  pause
  exit /b 1
)

echo [2/3] Menarik source terbaru dari GitHub...
git pull --ff-only
if errorlevel 1 (
  echo [GAGAL] git pull gagal. Ada perubahan lokal atau koneksi bermasalah.
  pause
  exit /b 1
)

echo [3/3] Build ulang dari source terbaru...
docker compose up -d --build
if errorlevel 1 goto FAILED
set "MODE=local"
goto DONE

:DONE
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
