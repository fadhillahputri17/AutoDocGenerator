AUTODOCGENERATOR - PEMBUATAN INSTALLER

File dalam paket:
1. AutoDocGenerator.iss
2. build_installer.bat
3. build_release.bat

TEMPAT MENYALIN
Salin ketiga file tersebut langsung ke:
D:\Project\AutoDocGenerator

STRUKTUR AKHIR
D:\Project\AutoDocGenerator
|-- AutoDocGenerator.iss
|-- build_installer.bat
|-- build_release.bat
|-- build_windows.bat
|-- AutoDocGenerator.spec
|-- launcher.py
|-- dist
|   `-- AutoDocGenerator
|       |-- AutoDocGenerator.exe
|       `-- file dan folder pendukung lainnya
`-- installer_output
    `-- AutoDocGenerator_Setup_0.1.0.exe

LANGKAH BUILD
1. Pastikan Inno Setup sudah terpasang.
2. Pastikan versi Python aplikasi lolos:
   ruff check src tests launcher.py
   pytest -q
3. Jalankan:
   build_release.bat

ATAU SECARA TERPISAH
1. build_windows.bat
2. build_installer.bat

HASIL AKHIR
installer_output\AutoDocGenerator_Setup_0.1.0.exe

File setup tersebut boleh dibagikan sebagai satu file installer.
Installer akan menyalin SELURUH isi dist\AutoDocGenerator, bukan hanya
AutoDocGenerator.exe.

CATATAN TESSERACT
Installer ini belum menyertakan Tesseract OCR. Komputer tujuan masih perlu
memiliki Tesseract, atau pengguna perlu memilih lokasi tesseract.exe melalui
form aplikasi.
