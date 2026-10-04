# MeTube-SRT

MeTube-SRT adalah turunan kecil dari [MeTube](https://github.com/alexta69/metube) yang menambahkan opsi **Download subtitle (SRT)** ke download video biasa.

## Rilis Windows terbaru

Rilis stabil pertama: **v1.0.0**

- Release: https://github.com/inoriko920-dev/MeTube-SRT/releases/tag/v1.0.0
- ZIP Windows: https://github.com/inoriko920-dev/MeTube-SRT/releases/download/v1.0.0/MeTube-SRT-Windows-v1.0.0.zip
- SHA-256: https://github.com/inoriko920-dev/MeTube-SRT/releases/download/v1.0.0/MeTube-SRT-Windows-v1.0.0.zip.sha256

Cara paling mudah: download ZIP, ekstrak, pastikan Docker Desktop aktif, lalu double-click `MULAI_MeTube-SRT.bat`.

Saat opsi SRT aktif:

- video tetap di-download seperti biasa;
- subtitle creator/manual diprioritaskan;
- jika subtitle manual tidak tersedia, caption auto-generated asli dipakai bila tersedia;
- auto-translate tidak diminta;
- subtitle dikonversi menjadi file `.srt` terpisah;
- pilihan berlaku juga untuk setiap video pada playlist dan channel.

Baseline upstream yang dipakai tercatat di [`UPSTREAM_COMMIT`](UPSTREAM_COMMIT).

## Cara termudah di Windows

Syarat utama: **Docker Desktop** sudah terpasang dan aktif.

Setelah repo di-download atau di-clone, pengguna Windows cukup memakai tiga file berikut:

```text
MULAI_MeTube-SRT.bat
HENTIKAN_MeTube-SRT.bat
UPDATE_MeTube-SRT.bat
```

### Menjalankan

Double-click:

```text
MULAI_MeTube-SRT.bat
```

Launcher akan:

1. memastikan Docker tersedia;
2. mencoba memakai image terbaru `ghcr.io/inoriko920-dev/metube-srt:latest`;
3. jika image GHCR tidak bisa dipull, otomatis fallback ke build source lokal;
4. membuat folder `downloads` jika belum ada;
5. menunggu aplikasi siap;
6. membuka `http://localhost:8081` otomatis di browser.

### Menghentikan

Double-click:

```text
HENTIKAN_MeTube-SRT.bat
```

Container akan dihentikan. File video dan SRT di folder `downloads` tidak dihapus.

### Update

Double-click:

```text
UPDATE_MeTube-SRT.bat
```

Updater akan mencoba mengambil image GHCR terbaru. Jika GHCR tidak tersedia, updater mencoba `git pull --ff-only` lalu build ulang source lokal.

## Menjalankan manual dengan Docker Compose

### Build lokal

```bash
git clone https://github.com/inoriko920-dev/MeTube-SRT.git
cd MeTube-SRT
docker compose up -d --build
```

Setelah container hidup, buka:

```text
http://localhost:8081
```

File hasil download disimpan di:

```text
./downloads
```

Untuk menghentikan aplikasi:

```bash
docker compose down
```

### Menggunakan image rilis GHCR

```bash
docker compose -f docker-compose.release.yml up -d
```

Image yang digunakan:

```text
ghcr.io/inoriko920-dev/metube-srt:latest
```

Jika package GHCR belum dapat dipull tanpa login, gunakan build lokal atau launcher Windows yang memiliki fallback otomatis.

## Cara memakai Video + SRT

1. Buka MeTube-SRT di browser.
2. Pilih download **Video**.
3. Centang **Download subtitle (SRT)** jika ingin subtitle.
4. Tempel URL video, playlist, atau channel.
5. Jalankan download.

Perilakunya:

| Pilihan | Hasil |
| --- | --- |
| SRT tidak dicentang | Video saja |
| SRT dicentang + subtitle tersedia | Video + `.srt` |
| SRT dicentang + hanya auto-caption asli tersedia | Video + `.srt` dari caption asli |
| SRT dicentang + tidak ada caption | Video tetap selesai tanpa `.srt` |

Contoh hasil:

```text
Judul Video.mp4
Judul Video.en.srt
```

Nama bahasa pada file SRT mengikuti track yang diberikan situs/yt-dlp.

## Playlist dan channel

Checkbox SRT diteruskan ke setiap item pada playlist/channel. Jadi cukup centang sekali sebelum memasukkan URL playlist atau channel.

Contoh:

```text
downloads/
└── Nama Playlist/
    ├── Video 01.mp4
    ├── Video 01.en.srt
    ├── Video 02.mp4
    ├── Video 02.en.srt
    └── ...
```

## Subtitle yang diambil

MeTube-SRT sengaja menghindari auto-translation.

Urutan yang dipakai:

1. subtitle manual/creator jika tersedia;
2. jika manual tidak ada, caption otomatis yang ditandai sebagai track asli;
3. jika tidak dapat menentukan track asli dengan aman, subtitle dilewati daripada mengambil terjemahan yang salah.

## Build dan test

CI repo memeriksa:

```text
Docker Compose lokal
Docker Compose release
Windows launcher files
PowerShell smoke-test syntax
Frontend lint
Frontend build
Frontend tests
Python compile
Backend tests
```

Test backend juga mencakup konfigurasi **video + SRT sidecar**.

### Tes nyata Video + SRT di Windows

GitHub-hosted runner dapat diblokir oleh anti-bot YouTube. Karena itu repo menyediakan skrip uji end-to-end yang dijalankan dari koneksi PC sendiri:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\test-youtube-srt.ps1
```

Skrip akan:

1. memastikan Docker aktif;
2. menjalankan `docker compose up -d --build`;
3. mengirim download cuplikan 3 detik dengan opsi SRT aktif;
4. menunggu antrean selesai;
5. memastikan benar-benar ada minimal satu file video dan satu file `.srt`.

Hasil uji disimpan terpisah di folder seperti:

```text
downloads/_smoke_srt_20261004-123456/
```

Untuk menguji URL lain:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\test-youtube-srt.ps1 -Url "https://www.youtube.com/watch?v=VIDEO_ID"
```

Pilih video yang memang memiliki subtitle manual atau auto-caption asli. Jika YouTube meminta verifikasi/cookie, skrip akan melaporkannya secara terpisah dan tidak menganggapnya sebagai keberhasilan aplikasi.

## Docker image otomatis

Workflow `.github/workflows/docker-publish.yml` membangun image multi-architecture:

```text
linux/amd64
linux/arm64
```

Image dipublikasikan ke:

```text
ghcr.io/inoriko920-dev/metube-srt
```

Tag utama:

```text
latest
sha-<commit>
v1.0.0
```

Tag Git seperti `v1.0.0` juga menghasilkan tag image dengan nama yang sama.

## Troubleshooting YouTube

YouTube dapat meminta cookie atau memblokir request tertentu. Karena MeTube-SRT tetap memakai yt-dlp, troubleshooting dasarnya sama dengan MeTube/yt-dlp.

Untuk masuk ke container:

```bash
docker exec -it metube-srt sh
```

Kemudian uji URL langsung dengan yt-dlp:

```bash
cd /downloads
yt-dlp --list-subs "URL_VIDEO"
```

Jika YouTube meminta login/cookie, gunakan mekanisme cookie MeTube seperti pada upstream.

## Update dari upstream MeTube

Repo ini menyimpan commit MeTube yang menjadi baseline di file [`UPSTREAM_COMMIT`](UPSTREAM_COMMIT). Saat mengambil update dari upstream, fitur MeTube-SRT perlu dipastikan tetap mempertahankan:

- checkbox `Download subtitle (SRT)`;
- flag subtitle pada API/backend;
- persistensi pilihan SRT;
- propagasi ke playlist/channel;
- filter caption asli agar tidak mengambil auto-translate;
- test `video + SRT sidecar`.

## Upstream

Project asal:

- MeTube: https://github.com/alexta69/metube
- yt-dlp: https://github.com/yt-dlp/yt-dlp

Dokumentasi konfigurasi lengkap MeTube tetap dapat digunakan untuk sebagian besar opsi server dan yt-dlp:

- https://github.com/alexta69/metube/wiki

## Lisensi

MeTube-SRT mengikuti lisensi source MeTube yang disertakan di [`LICENSE`](LICENSE).
