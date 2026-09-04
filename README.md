# Sistem Terpadu Absensi & Shift Kerja - PT. Lisa Concrete Indonesia

Sistem ini adalah aplikasi HRD mandiri (berbasis Streamlit) dengan fungsionalitas cerdas untuk pairing log absen mentah (fingerprint) dengan shift karyawan secara dinamis.

---

## 🛠 Struktur Direktori

Sistem ini telah ditata ulang (*MVC-like architecture*) agar rapi dan mudah dimaintenance:

```text
absensipy/
├── app/                  # (Core Application) Skrip dan Engine logika
│   ├── dashboard.py      # Antarmuka Pengguna Utama (Streamlit)
│   ├── pairing_engine.py # Otak algoritma deduplikasi & penentuan shift
│   └── export_hrd.py     # Modul konversi format ke HRD Legacy
├── database/             # (Storage) Penyimpanan Data
│   ├── active/           # Database berjalan (Generated CSVs)
│   │   ├── Raw_Logs.csv
│   │   ├── Hasil_Pairing_Absensi_Dengan_Shift_Revisi.csv
│   │   └── Laporan_Detail_Korban_Sistem_Lama.csv
│   └── master/           # File Referensi Konfigurasi & Seeders
│       ├── Data_Shift.csv
│       ├── Data_Kerja.csv
│       ├── t_dt_usr_akun.sql
│       ├── t_absensi_solutions_harian.sql
│       └── t_absensi_solutions_fp.sql
├── run.py                # Launcher Utama
├── requirements.txt      # Dependensi pustaka Python
└── README.md
```

## 🚀 Cara Menjalankan Aplikasi

1. Pastikan Python 3.9+ terinstal. Buka Terminal / Command Prompt di folder utama (`absensipy/`).
2. Instal *library* yang dibutuhkan (jika belum):
   ```bash
   pip install -r requirements.txt
   ```
3. Jalankan aplikasi melalui *launcher* utama:
   ```bash
   python run.py
   ```
4. Dashboard otomatis terbuka di browser pada alamat: `http://localhost:8501`.

## 📦 Fitur Unggulan

- **Anti-Duplikasi & Smart Merge**: Scan yang berulang dalam 1 jam diabaikan. Log lintas-hari untuk Shift Malam / Shift 3 tertata sempurna tanpa memotong hari.
- **Support Multiformat**: Tinggal drag & drop file dari mesin sidik jari dengan format SQL dump, Excel (`.xlsx`), CSV (`.csv`), atau `.dat` dari USB.
- **Export HRD**: Menghasilkan file CSV (`.csv`) yang 100% cocok dengan struktur database *payroll* perusahaan yang lama (beserta kalkulasi otomatis SPKL, Unit Lembur, dll).

*Siap diekstrak dan digunakan untuk operasional kantor!*
