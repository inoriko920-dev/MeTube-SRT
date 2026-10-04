# MeTube-SRT

MeTube-SRT adalah turunan kecil dari [MeTube](https://github.com/alexta69/metube) yang menambahkan opsi **Download subtitle (SRT)** ke download video biasa.

Saat opsi SRT aktif:

- video tetap di-download seperti biasa;
- subtitle creator/manual diprioritaskan;
- jika subtitle manual tidak tersedia, caption auto-generated asli dipakai bila tersedia;
- auto-translate tidak diminta;
- subtitle dikonversi menjadi file `.srt` terpisah;
- pilihan berlaku juga untuk setiap video pada playlist dan channel.

Baseline upstream yang dipakai tercatat di [`UPSTREAM_COMMIT`](UPSTREAM_COMMIT).

## Cara paling mudah menjalankan MeTube-SRT

### Opsi A — Build lokal dengan Docker Compose

Ini cara yang paling aman karena selalu memakai source dari repo ini.

```bash
git clone https://github.com/inoriko920-dev/MeTube-SRT.git
cd MeTube-SRT
docker compose up -d --build
```

Setelah container hidup, buka:

```text
http://localhost:8081
```

File hasil download disimpan di folder:

```text
./downloads
```

Untuk menghentikan aplikasi:

```bash
docker compose down
```

Untuk update ke source terbaru:

```bash
git pull
docker compose up -d --build
```

### Opsi B — Image GHCR

Repo ini memiliki workflow yang membangun image:

```text
ghcr.io/inoriko920-dev/metube-srt:latest
```

Jika package GHCR sudah dibuat public, image dapat dijalankan langsung:

```bash
docker run -d \
  --name metube-srt \
  -p 8081:8081 \
  -v ./downloads:/downloads \
  ghcr.io/inoriko920-dev/metube-srt:latest
```

Jika package belum public, gunakan **Opsi A** atau login ke GHCR terlebih dahulu.

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
Frontend lint
Frontend build
Frontend tests
Python compile
Backend tests
```

Test backend juga mencakup konfigurasi **video + SRT sidecar**.

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
