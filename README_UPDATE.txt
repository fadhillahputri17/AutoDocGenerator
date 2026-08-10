PEMBARUAN AUTODOCGENERATOR

Perubahan:
1. PDF di dalam folder NOTA REAL atau subfoldernya ikut dibaca.
2. Nama folder NOTA REAL toleran terhadap bentuk seperti Nota_Real dan NOTA-REAL.
3. Setiap halaman PDF dirender menjadi PNG tanpa crop, border, padding, atau square fit.
4. Gambar NOTA REAL dengan format yang didukung Word disalin byte-for-byte tanpa pemrosesan.
5. Gambar NOTA REAL tidak dibesarkan untuk memenuhi halaman Word; hanya dikecilkan proporsional bila terlalu besar.
6. Judul PDF tetap muncul satu kali di atas halaman pertama PDF.
7. Bukti transfer dipotong secara vertikal mulai tulisan "Transfer Dana ..." sampai baris "Diotorisasi".
8. Lebar asli transfer tetap dipertahankan dan tidak diberi border.

Salin isi folder paket ini ke root proyek:
D:\Project\AutoDocGenerator

Pilih Replace files in the destination untuk file dengan nama sama.

Setelah itu jalankan:
ruff check src tests launcher.py
pytest -q
python -m autodocgenerator

Tidak perlu menghapus file atau folder melalui command.
