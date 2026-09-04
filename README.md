# Sistem Terpadu Absensi & Shift Kerja - PT. Lisa Concrete Indonesia

Sistem ini adalah aplikasi HRD mandiri (berbasis Streamlit) yang memiliki fitur:
1. **Upload & Pairing Otomatis**: Mendukung file `.csv`, `.xlsx`, `.dat`, dan `.sql` langsung dari mesin fingerprint.
2. **Anti-Duplikasi & Smart Merge**: Scan yang sama tidak akan menumpuk. Karyawan yang lupa absen pulang otomatis disempurnakan jika file terbaru mengandung data pulang mereka.
3. **Optimasi Shift Malam**: Algoritma memfilter H-2 untuk menjaga agar shift malam tidak terpotong saat sinkronisasi harian.
4. **Ekspor HRD Legacy**: Hasil rekap absensi dapat diekspor menjadi `.csv` yang 100% kompatibel dengan format kolom software HRD kantor lama (termasuk *auto-fill* karyawan absen, perhitungan `PlgAk` dan `JmlLmbr`).

---

## Persiapan & Instalasi

Pastikan Anda sudah menginstal Python (disarankan versi 3.9+).

1. Buka Terminal / Command Prompt di folder ini.
2. Instal pustaka yang dibutuhkan:
   ```bash
   pip install -r requirements.txt
   ```

## Cara Menjalankan Aplikasi

Anda dapat menjalankan aplikasi Dashboard melalui salah satu cara berikut:

**Cara 1 (Langsung run script):**
```bash
python dashboard_run.py
```

**Cara 2 (Via Streamlit CLI):**
```bash
streamlit run dashboard.py
```

Aplikasi akan otomatis terbuka di browser Anda pada alamat `http://localhost:8501`.

---

## Penjelasan Isi File/Folder
Semua file belajar dan eksperimen telah dihapus. File yang tersisa adalah **kebutuhan inti** dari sistem ini:

### ⚙️ Inti Sistem (Source Code)
- `dashboard.py`: File utama antarmuka pengguna (UI).
- `pairing_engine.py`: Mesin utama (*core engine*) di balik layar yang menangani algoritma pairing, kalkulasi shift, dan deduplikasi.
- `export_hrd.py`: Modul khusus untuk menerjemahkan data rekap menjadi format CSV HRD lama (Legacy).
- `dashboard_run.py`: Script pembantu untuk menjalankan aplikasi.
- `requirements.txt`: Daftar pustaka Python (Streamlit, Pandas) yang harus diinstal.

### 🗄️ Database Primer (Jangan Dihapus)
- `Raw_Logs.csv`: Database yang menyimpan seluruh riwayat tap/scan jari mentah (yang sudah difilter anti-duplikat).
- `Hasil_Pairing_Absensi_Dengan_Shift_Revisi.csv`: Database hasil rekapitulasi masuk, pulang, shift, dan lembur (Data yang tampil di Dashboard).

### 🏢 Master Data & Referensi (Wajib Ada)
- `Data_Shift.csv`: Referensi master jam masuk dan pulang per departemen.
- `Data_Kerja.csv`: Referensi master NIP asli, jabatan, divisi, dan area kerja karyawan.
- `t_dt_usr_akun.sql`: Referensi metadata untuk menghubungkan PIN mesin dengan Nama asli karyawan.
- `t_absensi_solutions_harian.sql`: Data *boss/legacy* untuk keperluan komparasi (jika ingin mengecek anomali sistem lama).
- `t_absensi_solutions_fp.sql`: Backup inisialisasi *raw logs*.
- `Laporan_Detail_Korban_Sistem_Lama.csv`: Daftar riwayat histori anomali (opsional, bisa dibiarkan).

---
*Siap di-zip dan dikirim ke pihak kantor!*
