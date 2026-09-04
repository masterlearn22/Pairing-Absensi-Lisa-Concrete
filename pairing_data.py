import pandas as pd
import re

def parse_sql_dump(filepath):
    print(f"Membaca file {filepath}...")
    data = []
    pattern = re.compile(r"\('([^']*)',\s*'([^']*)',\s*'([^']*)',\s*(\d+),\s*'([^']*)'\)")
    
    with open(filepath, 'r', encoding='utf-8') as file:
        for line in file:
            if line.strip().startswith("('"):
                matches = pattern.findall(line)
                for match in matches:
                    area, pin, waktu, sts, waktu_tarik = match
                    data.append({
                        'Area': area,
                        'PIN': pin,
                        'Waktu_Scan': waktu,
                        'Status': int(sts)
                    })
    return pd.DataFrame(data)

def tentukan_shift(jam_masuk):
    # Jika tidak ada jam masuk (NaT / NaN), kembalikan Kosong
    if pd.isna(jam_masuk):
        return "Tidak Diketahui"
        
    # Konversi string jam 'HH:MM:SS' menjadi integer jam untuk kemudahan perbandingan
    # Mengambil dua karakter pertama dari 'HH:MM:SS'
    jam = int(str(jam_masuk)[:2])
    
    if 8 <= jam < 16:
        return "Shift 1 (08:00-16:00)"
    elif 16 <= jam <= 23:
        return "Shift 2 (16:00-00:00)"
    elif 0 <= jam < 8:
        return "Shift 3 (00:00-08:00)"
    else:
        return "Tidak Diketahui"

def main():
    df = parse_sql_dump('t_absensi_solutions_fp.sql')
    if df.empty:
        return
        
    df['Waktu_Scan'] = pd.to_datetime(df['Waktu_Scan'])
    df['Tanggal'] = df['Waktu_Scan'].dt.date
    
    # 1. Group By untuk Pairing Masuk & Keluar
    df_rekap = df.groupby(['PIN', 'Tanggal']).agg(
        Jam_Masuk=('Waktu_Scan', 'min'),
        Jam_Keluar=('Waktu_Scan', 'max'),
        Total_Scan=('Waktu_Scan', 'count')
    ).reset_index()
    
    # Extract only time
    df_rekap['Jam_Masuk'] = df_rekap['Jam_Masuk'].dt.strftime('%H:%M:%S')
    df_rekap['Jam_Keluar'] = df_rekap['Jam_Keluar'].dt.strftime('%H:%M:%S')
    
    # Kosongkan Jam_Keluar jika Total_Scan hanya 1
    df_rekap.loc[df_rekap['Total_Scan'] == 1, 'Jam_Keluar'] = "-"
    
    # 2. Proses Clustering Shift
    df_rekap['Shift'] = df_rekap['Jam_Masuk'].apply(tentukan_shift)
    
    # 3. Pairing Nama Karyawan
    dummy_karyawan = {
        '0189': 'Budi Santoso',
        '0190': 'Andi Kurniawan'
    }
    df_rekap['Nama_Karyawan'] = df_rekap['PIN'].map(dummy_karyawan).fillna("Karyawan " + df_rekap['PIN'])
    
    # 4. Susun ulang kolom
    df_after = df_rekap[['PIN', 'Nama_Karyawan', 'Tanggal', 'Shift', 'Jam_Masuk', 'Jam_Keluar', 'Total_Scan']]
    
    print("\n" + "="*80)
    print("DATA AFTER (Setelah Di-Pairing & Di-Clustering per Shift)")
    print("="*80)
    print(df_after.head(15).to_string(index=False))
    
    # Distribusi Karyawan di Tiap Shift
    print("\n" + "="*40)
    print("DISTRIBUSI DATA BERDASARKAN SHIFT")
    print("="*40)
    print(df_after['Shift'].value_counts().to_string())
    
    output_file = 'Hasil_Pairing_Absensi_Dengan_Shift.csv'
    df_after.to_csv(output_file, index=False)
    print(f"\n[+] Sukses! Data hasil pairing yang lengkap ({len(df_after)} baris) telah disimpan ke {output_file}")

if __name__ == "__main__":
    main()
