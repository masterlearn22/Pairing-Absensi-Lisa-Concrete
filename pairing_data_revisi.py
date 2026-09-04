import pandas as pd
import re

def parse_sql_dump(filepath):
    print(f"Membaca file {filepath}...")
    data = []
    
    # Menangkap Kode Area (kolom 1), PIN (kolom 2), Waktu_Scan (kolom 3)
    pattern = re.compile(r"\('([^']*)',\s*'([^']*)',\s*'([^']*)',\s*(\d+),\s*'([^']*)'\)")
    
    try:
        with open(filepath, 'r', encoding='utf-8') as file:
            for line in file:
                if line.strip().startswith("('"):
                    matches = pattern.findall(line)
                    for match in matches:
                        kode_area = match[0]
                        pin = match[1]
                        waktu_scan = match[2]
                        if pin and waktu_scan:
                            data.append({
                                'Kode_Area': kode_area,
                                'PIN': pin, 
                                'Waktu_Scan': waktu_scan
                            })
    except Exception as e:
        print(f"Gagal membaca {filepath}: {e}")
    return pd.DataFrame(data)

def parse_akun_dump(filepath):
    print(f"Membaca file data karyawan {filepath}...")
    akun_to_nama = {}
    akun_to_nip = {}
    # Capture: (usr), (akun), (nip), (nama)
    # INSERT INTO `tdt_usr_akun` (`usr`, `akun`, `nip`, `nama`, `tgl`) VALUES ('admin', '1', '216183', 'A. Jumain', ...)
    pattern = re.compile(r"\((?:'[^']*'|NULL),\s*'([^']*)',\s*(?:'([^']*)'|NULL),\s*(?:'([^']*)'|NULL)")
    
    try:
        with open(filepath, 'r', encoding='utf-8') as file:
            for line in file:
                if line.strip().startswith("('"):
                    matches = pattern.findall(line)
                    for match in matches:
                        akun, nip, nama = match
                        if nama and nama.strip():
                            akun_to_nama[akun] = nama
                        if nip and nip.strip():
                            akun_to_nip[akun] = nip
    except Exception as e:
        print(f"Gagal membaca {filepath}: {e}")
    return akun_to_nama, akun_to_nip

import os

if os.path.exists('Data_Shift.csv'):
    df_master_shift = pd.read_csv('Data_Shift.csv')
else:
    df_master_shift = pd.DataFrame()

def get_shift_category(name):
    s = str(name).upper()
    if 'OB' in s: return 'OB'
    if any(k in s for k in ['SECURITY', 'SECURTY', 'SATPAM']): return 'SECURITY'
    if 'FORMING' in s: return 'FORMING'
    if 'CASTING' in s: return 'CASTING'
    if any(k in s for k in ['MOJOKERTO', 'NGORO', 'SOLO', 'KUBU']): return 'EXTERNAL_BRANCH'
    if 'REPAIR' in s: return 'REPAIR'
    if 'QC' in s: return 'QC'
    if any(k in s for k in ['WAREHOUSE', 'INVENTORY']): return 'WAREHOUSE'
    if 'MAINTENANCE' in s: return 'MAINTENANCE'
    if 'HSE' in s: return 'HSE'
    if 'PPIC' in s: return 'PPIC'
    return 'UMUM'

if not df_master_shift.empty:
    df_master_shift['Kategori'] = df_master_shift['shiftkrj'].apply(get_shift_category)
    # Hapus shift cabang luar (Ngoro, Mojokerto, Solo, Kubu) agar tidak salah masuk ke pabrik SF/BF/SO
    df_master_shift = df_master_shift[df_master_shift['Kategori'] != 'EXTERNAL_BRANCH'].copy()

def tentukan_shift_cerdas(row, emp_dept_map):
    if 'Jam_Masuk_Asli' not in row or pd.isna(row['Jam_Masuk_Asli']):
        return "Tidak Diketahui"
        
    jam_masuk = row['Jam_Masuk_Asli']
    
    if df_master_shift.empty:
        jam = jam_masuk.hour
        if 5 <= jam < 11:
            return "Shift 1 (08:00-16:00)"
        elif 11 <= jam < 19:
            return "Shift 2 (16:00-00:00)"
        elif jam >= 19 or jam < 3:
            return "Shift 3 (00:00-08:00)"
        return "Shift Tidak Sesuai Jadwal"
        
    pin = str(row['PIN'])
    emp_dept = emp_dept_map.get(pin, 'UMUM')
    
    area = str(row['Kode_Area']).split(' / ')[0].strip()
    day_name = jam_masuk.strftime('%A').lower()
    is_saturday = day_name == 'saturday'
    is_sunday = day_name == 'sunday'
    
    dict_map = {
        '01': 'SO', '02': 'BO', '03': 'SF', '04': 'BF',
        'Surabaya Factory': 'SF', 'Bali Factory': 'BF',
        'Surabaya Office': 'SO', 'Bali Office': 'BO'
    }
    mapped_area = dict_map.get(area, area)
    
    valid_shifts = df_master_shift[(df_master_shift['Area'] == mapped_area) | (df_master_shift['Area'] == 'ALL')].copy()
    if valid_shifts.empty:
        valid_shifts = df_master_shift.copy()
        
    # Filter kandidat shift berdasarkan divisi / profesi karyawan:
    # Karyawan FORMING hanya mengambil FORMING (atau UMUM jika tidak ada shift forming)
    # Karyawan UMUM TIDAK BOLEH mengambil FORMING, CASTING, OB, SECURITY!
    if emp_dept == 'FORMING':
        forming_shifts = valid_shifts[valid_shifts['Kategori'] == 'FORMING']
        if not forming_shifts.empty:
            valid_shifts = pd.concat([forming_shifts, valid_shifts[valid_shifts['Kategori'] == 'UMUM']])
    elif emp_dept == 'CASTING':
        casting_shifts = valid_shifts[valid_shifts['Kategori'] == 'CASTING']
        if not casting_shifts.empty:
            valid_shifts = pd.concat([casting_shifts, valid_shifts[valid_shifts['Kategori'] == 'UMUM']])
    elif emp_dept == 'SECURITY':
        sec_shifts = valid_shifts[valid_shifts['Kategori'] == 'SECURITY']
        if not sec_shifts.empty:
            valid_shifts = sec_shifts
    elif emp_dept == 'OB':
        ob_shifts = valid_shifts[valid_shifts['Kategori'] == 'OB']
        if not ob_shifts.empty:
            valid_shifts = ob_shifts
    else: # UMUM / Staff / Produksi Biasa
        valid_shifts = valid_shifts[valid_shifts['Kategori'] == 'UMUM']
        
    min_diff = float('inf')
    best_shift_name = "Shift Tidak Ditemukan"
    in_time_minutes = jam_masuk.hour * 60 + jam_masuk.minute
    
    for _, shift in valid_shifts.iterrows():
        shift_name = str(shift['shiftkrj']).upper()
        jat_str = str(shift['JAT'])
        try:
            h, m = map(int, jat_str.split(':'))
            jat_minutes = h * 60 + m
        except:
            continue
            
        diff = abs(in_time_minutes - jat_minutes)
        diff = min(diff, 24 * 60 - diff)
        
        penalty = 0
        # Prioritas kuat untuk shift yang sesuai dengan divisinya sendiri
        if emp_dept in ['FORMING', 'CASTING'] and shift['Kategori'] == emp_dept:
            penalty -= 300 # Bonus kuat agar tetap di divisinya
            
        if is_saturday:
            if 'SABTU' in shift_name:
                penalty -= 120
            elif 'MINGGU' in shift_name:
                penalty += 360
        elif is_sunday:
            if 'MINGGU' in shift_name:
                penalty -= 120
            elif 'SABTU' in shift_name:
                penalty += 360
        else:
            if 'SABTU' in shift_name or 'MINGGU' in shift_name:
                penalty += 360
                
        total_diff = diff + penalty
        if total_diff < min_diff:
            min_diff = total_diff
            best_shift_name = f"{shift['shiftkrj']} ({jat_str}-{shift['JST']})"
            
    return best_shift_name

def main():
    df = parse_sql_dump('t_absensi_solutions_fp.sql')
    if df.empty:
        return
        
    df['Waktu_Scan'] = pd.to_datetime(df['Waktu_Scan'])
    df = df.sort_values(['PIN', 'Waktu_Scan'])
    
    # -------------------------------------------------------------
    # PEMBERSIHAN DATA: Hapus Double Scan (Selisih kurang dari 1 jam pada area yang sama)
    # -------------------------------------------------------------
    df['Prev_Scan'] = df.groupby(['PIN', 'Kode_Area'])['Waktu_Scan'].shift(1)
    df['Selisih_Jam'] = (df['Waktu_Scan'] - df['Prev_Scan']).dt.total_seconds() / 3600
    df = df[df['Selisih_Jam'].isna() | (df['Selisih_Jam'] >= 1.0)].copy()
    
    records = []
    # KELOMPOKKAN BERDASARKAN PIN DAN KODE AREA (Agar tidak tercampur jika 1 PIN dipakai di 2 pabrik berbeda)
    for (pin, kode_area), group in df.groupby(['PIN', 'Kode_Area']):
        scans = group['Waktu_Scan'].tolist()
        areas = group['Kode_Area'].tolist() if 'Kode_Area' in group.columns else [""] * len(scans)
        
        i = 0
        while i < len(scans):
            in_time = scans[i]
            in_area = areas[i]
            out_time = pd.NaT
            out_area = "-"
            
            # Cari scan berikutnya sebagai jam keluar
            if i + 1 < len(scans):
                duration = (scans[i+1] - in_time).total_seconds() / 3600
                if duration <= 17:
                    # Pasangan Masuk - Keluar yang valid
                    out_time = scans[i+1]
                    out_area = areas[i+1]
                    i += 2
                else:
                    # Lupa absen keluar
                    i += 1
            else:
                i += 1
                
            # Tambahkan Keterangan untuk mempermudah HRD
            keterangan = "Normal"
            if pd.isna(out_time):
                keterangan = "Lupa Absen Keluar (Input Manual)"
            else:
                dur = (out_time - in_time).total_seconds() / 3600
                if dur > 9: # Jika lebih dari 9 jam, terhitung lembur
                    jam_l = int(dur - 8)
                    keterangan = f"Ada Lembur (+/- {jam_l} Jam)"
                
            # Gabungkan Kode Area masuk dan keluar (jika ada)
            kode_area_gabung = str(in_area)
            if not pd.isna(out_time) and out_area != str(in_area):
                kode_area_gabung += f" / {out_area}"
                
            records.append({
                'PIN': pin,
                'Tanggal': in_time.date(),
                'Kode_Area': kode_area_gabung,
                'Jam_Masuk': in_time,
                'Jam_Keluar': out_time,
                'Total_Scan': 2 if not pd.isna(out_time) else 1,
                'Keterangan': keterangan
            })
            
    df_rekap = pd.DataFrame(records)
    
    # Format jam ke string
    df_rekap['Jam_Masuk_Asli'] = df_rekap['Jam_Masuk']
    df_rekap['Jam_Masuk'] = df_rekap['Jam_Masuk'].dt.strftime('%H:%M:%S')
    df_rekap['Jam_Keluar'] = df_rekap['Jam_Keluar'].dt.strftime('%H:%M:%S').fillna("-")
    
    # 2. Pairing Nama Karyawan
    akun_to_nama, akun_to_nip = parse_akun_dump('t_dt_usr_akun.sql')
    
    df_rekap['Nama_Karyawan'] = df_rekap['PIN'].map(akun_to_nama).fillna("Karyawan " + df_rekap['PIN'])
    df_rekap['NIP_Asli'] = df_rekap['PIN'].map(akun_to_nip).fillna(df_rekap['PIN'])
    
    # 3. Mapping Kode Area
    dict_area = {
        'BF': 'Bali Factory',
        'SF': 'Surabaya Factory',
        'SO': 'Surabaya Office'
    }
    
    # Fungsi untuk mereplace jika ada format gabungan (misal 'BF / SF')
    def map_area(kode_str):
        if pd.isna(kode_str) or not kode_str:
            return "-"
        
        parts = [p.strip() for p in kode_str.split('/')]
        mapped_parts = [dict_area.get(p, p) for p in parts]
        return " / ".join(mapped_parts)
        
    df_rekap['Kode_Area'] = df_rekap['Kode_Area'].apply(map_area)
    
    # 4. Merge Data Karyawan (Lokasi Kerja Asli)
    if os.path.exists('Data_Kerja.csv'):
        df_kerja = pd.read_csv('Data_Kerja.csv')
        df_kerja['PIN'] = df_kerja['PIN'].astype(str)
        df_rekap['NIP_Asli'] = df_rekap['NIP_Asli'].astype(str)
        # Ambil kolom Lokasi_Kerja_Asli dan drop duplicates jika 1 NIP punya multiple record
        df_kerja_unique = df_kerja[['PIN', 'Lokasi_Kerja_Asli', 'kd_jabatan', 'kd_divisi']].drop_duplicates(subset=['PIN'], keep='last')
        df_rekap = pd.merge(df_rekap, df_kerja_unique, left_on='NIP_Asli', right_on='PIN', how='left', suffixes=('', '_kerja'))
        df_rekap['Lokasi_Kerja_Asli'] = df_rekap['Lokasi_Kerja_Asli'].fillna('Tidak Ditemukan')
        df_rekap['Kode_Jabatan'] = df_rekap['kd_jabatan'].fillna('-')
        df_rekap['Kode_Divisi'] = df_rekap['kd_divisi'].fillna('-')
    else:
        df_rekap['Lokasi_Kerja_Asli'] = 'Tidak Diketahui'
        df_rekap['Kode_Jabatan'] = '-'
        df_rekap['Kode_Divisi'] = '-'

    # 5. Pemetaan Profil Divisi Karyawan (Mencegah salah shift ke OB, Security, dsb)
    print("Menganalisis profil divisi & pola kerja karyawan...")
    emp_dept_map = {}
    for pin_val, group in df_rekap.groupby('PIN'):
        pin_str = str(pin_val)
        weekday_group = group[pd.to_datetime(group['Tanggal']).dt.dayofweek < 5]
        if weekday_group.empty:
            weekday_group = group
        times = weekday_group['Jam_Masuk_Asli'].dropna()
        if times.empty:
            emp_dept_map[pin_str] = 'UMUM'
            continue
        hours = times.dt.hour
        # Siklus Forming: Jam 7 (Shift 1), Jam 15 (Shift 2), Jam 23 (Shift 3)
        forming_count = ((hours == 6) | (hours == 7) | (hours == 14) | (hours == 15) | (hours == 22) | (hours == 23)).sum()
        ratio = forming_count / len(times)
        area_first = str(group['Kode_Area'].iloc[0])
        if 'Surabaya' in area_first or 'SF' in area_first:
            if ratio >= 0.35:
                emp_dept_map[pin_str] = 'FORMING'
            else:
                emp_dept_map[pin_str] = 'UMUM'
        else:
            emp_dept_map[pin_str] = 'UMUM'

    # 6. Menentukan Shift yang Tepat Sesuai Divisi Karyawan
    print("Menentukan shift kerja secara dinamis dan konsisten...")
    df_rekap['Shift'] = df_rekap.apply(lambda r: tentukan_shift_cerdas(r, emp_dept_map), axis=1)
    
    df_after = df_rekap[['PIN', 'Nama_Karyawan', 'Lokasi_Kerja_Asli', 'Kode_Jabatan', 'Kode_Divisi', 'Tanggal', 'Kode_Area', 'Shift', 'Jam_Masuk', 'Jam_Keluar', 'Total_Scan', 'Keterangan']]
    
    print("\n" + "="*80)
    print("DATA AFTER (Setelah Di-Pairing & Di-Clustering per Shift - LOGIC BARU)")
    print("="*80)
    print(df_after.head(15).to_string(index=False))
    
    print("\n" + "="*40)
    print("DISTRIBUSI DATA BERDASARKAN SHIFT (REVISI)")
    print("="*40)
    print(df_after['Shift'].value_counts().to_string())
    
    output_file = 'Hasil_Pairing_Absensi_Dengan_Shift_Revisi.csv'
    df_after.to_csv(output_file, index=False)
    print(f"\n[+] Sukses! Data hasil revisi ({len(df_after)} baris) telah disimpan ke {output_file}")

if __name__ == "__main__":
    main()
