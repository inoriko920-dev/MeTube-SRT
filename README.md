# MeTube-SRT

MeTube-SRT adalah mod ringan dari [MeTube](https://github.com/alexta69/metube) untuk menambahkan satu opsi sederhana pada download video:

- **Download subtitle (SRT)** tidak dicentang → video saja.
- **Download subtitle (SRT)** dicentang → video + subtitle SRT.
- Subtitle **tidak diterjemahkan** oleh aplikasi.
- Jika subtitle manual tersedia, subtitle manual diprioritaskan.
- Jika subtitle manual tidak tersedia, caption auto-generated asli dari YouTube digunakan bila tersedia.
- Berlaku pada download video tunggal, playlist, dan channel yang ditambahkan melalui tombol **Download**.

Repo ini menggunakan source MeTube upstream sebagai baseline dan menyimpan commit upstream yang dipakai di `UPSTREAM_COMMIT`.

## Lisensi

MeTube-SRT merupakan karya turunan MeTube dan mengikuti lisensi upstream. Source upstream, copyright notice, dan file `LICENSE` dipertahankan saat source di-bootstrap.
