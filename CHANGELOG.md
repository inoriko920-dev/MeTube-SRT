# Changelog

## v1.0.1

Patch rilis Windows/distribusi.

- Paket Windows versi release sekarang mengunci Docker image ke tag release yang sama, bukan `latest`.
- `MULAI_MeTube-SRT.bat` membaca `VERSI_IMAGE.txt` dan menjalankan image yang dipilih.
- `UPDATE_MeTube-SRT.bat` mencari GitHub Release stabil terbaru lalu menyimpan tag yang dipakai.
- `docker-compose.release.yml` menerima `METUBE_SRT_IMAGE_TAG`.
- Workflow paket Windows memverifikasi isi ZIP, versi image, dan SHA-256.
- Fallback build source lokal tetap tersedia jika image rilis tidak dapat dipakai.

## v1.0.0

Rilis pertama MeTube-SRT.

- Checkbox **Download subtitle (SRT)** untuk download video.
- Subtitle manual/creator diprioritaskan.
- Jika manual tidak tersedia, caption auto-generated asli dapat digunakan.
- Auto-translate tidak diminta.
- Berlaku untuk video tunggal, playlist, dan channel.
- Windows launcher mulai/hentikan/update.
- Docker image GHCR dan paket Windows ZIP.
