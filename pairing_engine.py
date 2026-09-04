import os
import re
import io
import datetime
import pandas as pd

# Mapping Area standar
DICT_AREA_NAMES = {
    'BF': 'Bali Factory',
    'SF': 'Surabaya Factory',
    'SO': 'Surabaya Office',
    'BO': 'Bali Office',
    '01': 'Surabaya Office',
    '02': 'Bali Office',
    '03': 'Surabaya Factory',
    '04': 'Bali Factory'
}

DICT_AREA_CODES = {
    '01': 'SO', '02': 'BO', '03': 'SF', '04': 'BF',
    'Surabaya Factory': 'SF', 'Bali Factory': 'BF',
    'Surabaya Office': 'SO', 'Bali Office': 'BO',
    'SF': 'SF', 'BF': 'BF', 'SO': 'SO', 'BO': 'BO'
}

RAW_LOGS_FILE = 'Raw_Logs.csv'
PAIRED_FILE = 'Hasil_Pairing_Absensi_Dengan_Shift_Revisi.csv'
SHIFT_FILE = 'Data_Shift.csv'
KERJA_FILE = 'Data_Kerja.csv'
AKUN_FILE = 't_dt_usr_akun.sql'
INITIAL_SQL_FILE = 't_absensi_solutions_fp.sql'


def get_shift_category(name):
    s = str(name).upper()
    if 'OB' in s:
        return 'OB'
    if any(k in s for k in ['SECURITY', 'SECURTY', 'SATPAM']):
        return 'SECURITY'
    if 'FORMING' in s:
        return 'FORMING'
    if 'CASTING' in s:
        return 'CASTING'
    if any(k in s for k in ['MOJOKERTO', 'NGORO', 'SOLO', 'KUBU']):
        return 'EXTERNAL_BRANCH'
    if 'REPAIR' in s:
        return 'REPAIR'
    if 'QC' in s:
        return 'QC'
    if any(k in s for k in ['WAREHOUSE', 'INVENTORY']):
        return 'WAREHOUSE'
    if 'MAINTENANCE' in s:
        return 'MAINTENANCE'
    if 'HSE' in s:
        return 'HSE'
    if 'PPIC' in s:
        return 'PPIC'
    return 'UMUM'


class ShiftClassifier:
    """Kelas pengklasifikasi shift berkecepatan tinggi menggunakan pre-compiled list/dict."""

    def __init__(self, shift_csv_path=SHIFT_FILE):
        self.shifts = []
        if os.path.exists(shift_csv_path):
            df_shift = pd.read_csv(shift_csv_path)
            if not df_shift.empty:
                df_shift['Kategori'] = df_shift['shiftkrj'].apply(get_shift_category)
                df_shift = df_shift[df_shift['Kategori'] != 'EXTERNAL_BRANCH'].copy()
                for row in df_shift.to_dict('records'):
                    jat_str = str(row.get('JAT', '08:00')).strip()
                    jst_str = str(row.get('JST', '16:00')).strip()
                    try:
                        parts = jat_str.split(':')
                        h, m = int(parts[0]), int(parts[1])
                        jat_min = h * 60 + m
                    except Exception:
                        continue
                    self.shifts.append({
                        'shiftkrj': str(row.get('shiftkrj', '')),
                        'Area': str(row.get('Area', 'ALL')).strip(),
                        'Kategori': row['Kategori'],
                        'JAT': jat_str,
                        'JST': jst_str,
                        'jat_min': jat_min,
                        'shift_upper': str(row.get('shiftkrj', '')).upper()
                    })

    def determine_shift(self, jam_masuk, area, emp_dept):
        if jam_masuk is None or pd.isna(jam_masuk):
            return "Tidak Diketahui"

        if not self.shifts:
            jam = jam_masuk.hour
            if 5 <= jam < 11:
                return "Shift 1 (08:00-16:00)"
            elif 11 <= jam < 19:
                return "Shift 2 (16:00-00:00)"
            elif jam >= 19 or jam < 3:
                return "Shift 3 (00:00-08:00)"
            return "Shift Tidak Sesuai Jadwal"

        raw_area = str(area).split(' / ')[0].strip()
        mapped_area = DICT_AREA_CODES.get(raw_area, raw_area)
        day_name = jam_masuk.strftime('%A').lower()
        is_saturday = (day_name == 'saturday')
        is_sunday = (day_name == 'sunday')

        # Filter berdasarkan area
        valid = [s for s in self.shifts if s['Area'] == mapped_area or s['Area'] == 'ALL']
        if not valid:
            valid = self.shifts

        # Filter berdasarkan departemen karyawan
        if emp_dept == 'FORMING':
            candidates = [s for s in valid if s['Kategori'] in ('FORMING', 'UMUM')]
        elif emp_dept == 'CASTING':
            candidates = [s for s in valid if s['Kategori'] in ('CASTING', 'UMUM')]
        elif emp_dept == 'SECURITY':
            candidates = [s for s in valid if s['Kategori'] == 'SECURITY'] or valid
        elif emp_dept == 'OB':
            candidates = [s for s in valid if s['Kategori'] == 'OB'] or valid
        else:
            candidates = [s for s in valid if s['Kategori'] == 'UMUM']

        if not candidates:
            candidates = valid

        in_time_minutes = jam_masuk.hour * 60 + jam_masuk.minute
        min_diff = float('inf')
        best_shift_name = "Shift Tidak Ditemukan"

        for s in candidates:
            diff = abs(in_time_minutes - s['jat_min'])
            if diff > 720:
                diff = 1440 - diff

            penalty = 0
            if emp_dept in ('FORMING', 'CASTING') and s['Kategori'] == emp_dept:
                penalty -= 300

            shift_name = s['shift_upper']
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
                best_shift_name = f"{s['shiftkrj']} ({s['JAT']}-{s['JST']})"

        return best_shift_name


def parse_sql_text(text_content):
    """Mengekstrak data scan dari string SQL dump."""
    pattern = re.compile(r"\('([^']*)',\s*'([^']*)',\s*'([^']*)',\s*(\d+),\s*'([^']*)'\)")
    data = []
    for match in pattern.findall(text_content):
        kode_area = match[0].strip()
        pin = match[1].strip()
        waktu_scan = match[2].strip()
        status = int(match[3]) if match[3].isdigit() else 0
        if pin and waktu_scan:
            data.append({
                'Kode_Area': kode_area,
                'PIN': pin,
                'Waktu_Scan': waktu_scan,
                'Status': status
            })
    return pd.DataFrame(data)


def parse_dat_or_txt(content, default_area='SF'):
    """Mengekstrak log dari format text/dat (misal attlog.dat USB fingerprint)."""
    lines = content.splitlines()
    data = []
    # Pattern 1: (PIN) (YYYY-MM-DD HH:MM:SS) (STATUS opsional)
    pat1 = re.compile(r"^[\s\"']*([A-Za-z0-9_-]+)[\s\t,;]+(\d{4}[-/]\d{1,2}[-/]\d{1,2}[\sT]\d{1,2}:\d{2}(?::\d{2})?)(?:[\s\t,;]+(\d+))?")
    # Pattern 2: (PIN) (DD-MM-YYYY HH:MM:SS)
    pat2 = re.compile(r"^[\s\"']*([A-Za-z0-9_-]+)[\s\t,;]+(\d{1,2}[-/]\d{1,2}[-/]\d{4}[\sT]\d{1,2}:\d{2}(?::\d{2})?)(?:[\s\t,;]+(\d+))?")

    for line in lines:
        line_s = line.strip()
        if not line_s or line_s.startswith('#') or line_s.startswith('//'):
            continue
        m = pat1.match(line_s)
        if not m:
            m = pat2.match(line_s)
        if m:
            pin = m.group(1).strip()
            waktu_str = m.group(2).strip().replace('/', '-')
            status = int(m.group(3)) if (m.group(3) and m.group(3).isdigit()) else 0
            data.append({
                'Kode_Area': default_area,
                'PIN': pin,
                'Waktu_Scan': waktu_str,
                'Status': status
            })
    return pd.DataFrame(data)


def parse_tabular_dataframe(df, default_area='SF'):
    """Standarisasi kolom dataframe dari hasil read_csv atau read_excel."""
    if df.empty:
        return pd.DataFrame(columns=['Kode_Area', 'PIN', 'Waktu_Scan', 'Status'])

    col_map = {}
    for col in df.columns:
        c_clean = str(col).strip().lower().replace('_', '').replace(' ', '')
        if c_clean in ['pin', 'nip', 'nik', 'userid', 'id', 'badgenumber', 'noid', 'no.id', 'akun', 'pinabsen']:
            col_map[col] = 'PIN'
        elif c_clean in ['waktu', 'waktuscan', 'scantime', 'datetime', 'tanggal&waktu', 'tanggalwaktu', 'jam', 'timestamp', 'date/time']:
            col_map[col] = 'Waktu_Scan'
        elif c_clean in ['area', 'kodearea', 'lokasi', 'mesin', 'namamesin', 'terminal', 'device']:
            col_map[col] = 'Kode_Area'
        elif c_clean in ['status', 'sts', 'state', 'inout', 'type', 'statusabsen']:
            col_map[col] = 'Status'

    df_norm = df.rename(columns=col_map).copy()

    # Cek apakah kolom wajib PIN dan Waktu_Scan ada
    if 'PIN' not in df_norm.columns or 'Waktu_Scan' not in df_norm.columns:
        for col in df_norm.columns:
            if col != 'PIN' and 'Waktu_Scan' not in df_norm.columns:
                try:
                    sample = pd.to_datetime(df_norm[col].dropna().head(10))
                    if not sample.empty:
                        df_norm['Waktu_Scan'] = df_norm[col]
                        break
                except Exception:
                    pass

    if 'PIN' not in df_norm.columns or 'Waktu_Scan' not in df_norm.columns:
        raise ValueError("File harus memiliki kolom identitas karyawan (PIN/NIP/No ID) dan Waktu Scan.")

    if 'Kode_Area' not in df_norm.columns:
        df_norm['Kode_Area'] = default_area
    else:
        df_norm['Kode_Area'] = df_norm['Kode_Area'].fillna(default_area).astype(str)

    if 'Status' not in df_norm.columns:
        df_norm['Status'] = 0

    df_norm['PIN'] = df_norm['PIN'].astype(str).str.strip()
    df_norm['Kode_Area'] = df_norm['Kode_Area'].astype(str).str.strip()
    df_norm['Waktu_Scan'] = df_norm['Waktu_Scan'].astype(str).str.strip()

    return df_norm[['Kode_Area', 'PIN', 'Waktu_Scan', 'Status']].dropna(subset=['PIN', 'Waktu_Scan'])


def parse_fingerprint_file(file_obj, filename, default_area='SF'):
    """
    Parser universal untuk berbagai format ekspor log fingerprint:
    .sql, .csv, .xlsx, .xls, .dat, .txt
    """
    ext = os.path.splitext(filename)[1].lower()

    if hasattr(file_obj, 'read'):
        raw_bytes = file_obj.read()
    elif isinstance(file_obj, (str, os.PathLike)):
        with open(file_obj, 'rb') as f:
            raw_bytes = f.read()
    else:
        raw_bytes = bytes(file_obj)

    if ext == '.sql':
        text = raw_bytes.decode('utf-8', errors='ignore')
        df = parse_sql_text(text)
        if df.empty:
            df = parse_dat_or_txt(text, default_area=default_area)
    elif ext in ('.xlsx', '.xls'):
        df_raw = pd.read_excel(io.BytesIO(raw_bytes), dtype=str)
        df = parse_tabular_dataframe(df_raw, default_area=default_area)
    elif ext == '.csv':
        try:
            text_sample = raw_bytes[:4096].decode('utf-8', errors='ignore')
            sep = ';' if text_sample.count(';') > text_sample.count(',') else (
                '\t' if text_sample.count('\t') > text_sample.count(',') else ','
            )
            df_raw = pd.read_csv(io.BytesIO(raw_bytes), sep=sep, dtype=str)
            df = parse_tabular_dataframe(df_raw, default_area=default_area)
        except Exception:
            text = raw_bytes.decode('utf-8', errors='ignore')
            df = parse_dat_or_txt(text, default_area=default_area)
    elif ext in ('.dat', '.txt'):
        text = raw_bytes.decode('utf-8', errors='ignore')
        df = parse_dat_or_txt(text, default_area=default_area)
    else:
        text = raw_bytes.decode('utf-8', errors='ignore')
        df = parse_sql_text(text)
        if df.empty:
            df = parse_dat_or_txt(text, default_area=default_area)

    if df.empty:
        raise ValueError(f"Tidak ada data log fingerprint valid yang dapat diekstrak dari {filename}.")

    df['PIN'] = df['PIN'].astype(str).str.strip()
    df['Waktu_Scan'] = pd.to_datetime(df['Waktu_Scan'], errors='coerce')
    df = df.dropna(subset=['Waktu_Scan']).copy()
    df['Waktu_Scan'] = df['Waktu_Scan'].dt.strftime('%Y-%m-%d %H:%M:%S')

    return df[['Kode_Area', 'PIN', 'Waktu_Scan', 'Status']]


def bootstrap_raw_logs():
    """Membuat Raw_Logs.csv awal dari t_absensi_solutions_fp.sql jika belum ada."""
    if os.path.exists(RAW_LOGS_FILE):
        return

    print(f"Inisialisasi {RAW_LOGS_FILE} dari {INITIAL_SQL_FILE}...")
    if not os.path.exists(INITIAL_SQL_FILE):
        pd.DataFrame(columns=['Kode_Area', 'PIN', 'Waktu_Scan', 'Status']).to_csv(RAW_LOGS_FILE, index=False)
        return

    with open(INITIAL_SQL_FILE, 'r', encoding='utf-8', errors='ignore') as f:
        text = f.read()
    df = parse_sql_text(text)
    if not df.empty:
        df['PIN'] = df['PIN'].astype(str).str.strip()
        df['Waktu_Scan'] = pd.to_datetime(df['Waktu_Scan'], errors='coerce')
        df = df.dropna(subset=['Waktu_Scan']).sort_values(['PIN', 'Waktu_Scan'])
        df['Waktu_Scan'] = df['Waktu_Scan'].dt.strftime('%Y-%m-%d %H:%M:%S')
        df = df.drop_duplicates(subset=['PIN', 'Waktu_Scan', 'Kode_Area'], keep='first')
        df.to_csv(RAW_LOGS_FILE, index=False)
        print(f"Inisialisasi selesai: {len(df)} log tersimpan di {RAW_LOGS_FILE}")
    else:
        pd.DataFrame(columns=['Kode_Area', 'PIN', 'Waktu_Scan', 'Status']).to_csv(RAW_LOGS_FILE, index=False)


def ingest_raw_logs(new_df, raw_logs_path=RAW_LOGS_FILE):
    """
    Menyimpan log mentah ke Raw_Logs.csv dengan anti-duplikasi.
    Mengembalikan: (df_merged_all, total_scans_in_file, new_scans_added, duplicate_scans_skipped)
    """
    bootstrap_raw_logs()

    total_uploaded = len(new_df)
    if total_uploaded == 0:
        if os.path.exists(raw_logs_path):
            df_existing = pd.read_csv(raw_logs_path)
        else:
            df_existing = pd.DataFrame(columns=['Kode_Area', 'PIN', 'Waktu_Scan', 'Status'])
        return df_existing, 0, 0, 0

    if os.path.exists(raw_logs_path):
        df_existing = pd.read_csv(raw_logs_path, dtype={'PIN': str})
        df_existing['PIN'] = df_existing['PIN'].astype(str).str.strip()
        df_existing['Waktu_Scan'] = df_existing['Waktu_Scan'].astype(str).str.strip()
        df_existing['Kode_Area'] = df_existing['Kode_Area'].astype(str).str.strip()
    else:
        df_existing = pd.DataFrame(columns=['Kode_Area', 'PIN', 'Waktu_Scan', 'Status'])

    new_clean = new_df.copy()
    new_clean['PIN'] = new_clean['PIN'].astype(str).str.strip()
    new_clean['Waktu_Scan'] = new_clean['Waktu_Scan'].astype(str).str.strip()
    new_clean['Kode_Area'] = new_clean['Kode_Area'].astype(str).str.strip()
    new_clean = new_clean.drop_duplicates(subset=['PIN', 'Waktu_Scan', 'Kode_Area'], keep='first')

    if not df_existing.empty:
        # Gunakan kombinasi PIN dinormalisasi (tanpa leading zero) + Waktu_Scan + Kode_Area
        def make_key(p, w, a):
            p_norm = str(p).lstrip('0') or '0'
            return f"{p_norm}__{w}__{a}"

        existing_keys = set(df_existing.apply(lambda r: make_key(r['PIN'], r['Waktu_Scan'], r['Kode_Area']), axis=1))
        new_clean['key'] = new_clean.apply(lambda r: make_key(r['PIN'], r['Waktu_Scan'], r['Kode_Area']), axis=1)
        mask_new = ~new_clean['key'].isin(existing_keys)
        new_records = new_clean[mask_new].drop(columns=['key'])
        duplicate_count = len(new_clean) - len(new_records) + (total_uploaded - len(new_clean))
        new_count = len(new_records)
    else:
        new_records = new_clean
        new_count = len(new_records)
        duplicate_count = total_uploaded - new_count

    if new_count > 0:
        df_combined = pd.concat([df_existing, new_records], ignore_index=True)
        df_combined = df_combined.sort_values(['PIN', 'Waktu_Scan'])
        df_combined.to_csv(raw_logs_path, index=False)
    else:
        df_combined = df_existing

    return df_combined, total_uploaded, new_count, duplicate_count


def load_employee_metadata():
    """Memuat metadata nama karyawan, NIP asli, dan lokasi kerja."""
    akun_to_nama = {}
    akun_to_nip = {}

    if os.path.exists(AKUN_FILE):
        pattern = re.compile(r"\((?:'[^']*'|NULL),\s*'([^']*)',\s*(?:'([^']*)'|NULL),\s*(?:'([^']*)'|NULL)")
        try:
            with open(AKUN_FILE, 'r', encoding='utf-8', errors='ignore') as f:
                for line in f:
                    if line.strip().startswith("('"):
                        for match in pattern.findall(line):
                            akun, nip, nama = match
                            if nama and nama.strip():
                                akun_to_nama[akun.strip()] = nama.strip()
                            if nip and nip.strip():
                                akun_to_nip[akun.strip()] = nip.strip()
        except Exception as e:
            print(f"Gagal membaca metadata akun: {e}")

    df_kerja_unique = pd.DataFrame()
    if os.path.exists(KERJA_FILE):
        try:
            df_kerja = pd.read_csv(KERJA_FILE)
            df_kerja['PIN'] = df_kerja['PIN'].astype(str).str.strip()
            df_kerja_unique = df_kerja[['PIN', 'Lokasi_Kerja_Asli', 'kd_jabatan', 'kd_divisi']].drop_duplicates(subset=['PIN'], keep='last')
        except Exception as e:
            print(f"Gagal membaca Data_Kerja.csv: {e}")

    return akun_to_nama, akun_to_nip, df_kerja_unique


def run_pairing_process(df_raw, classifier=None):
    """
    Menjalankan algoritma pairing berkecepatan tinggi pada sekumpulan log mentah:
    1. Filter double-scan (< 1 jam pada area yang sama).
    2. Pairing Masuk - Keluar (durasi <= 17 jam).
    3. Penentuan shift cerdas per profil departemen.
    4. Mapping data karyawan & lokasi kerja.
    """
    if df_raw.empty:
        return pd.DataFrame()

    if classifier is None:
        classifier = ShiftClassifier()

    df = df_raw.copy()
    df['Waktu_Scan'] = pd.to_datetime(df['Waktu_Scan'])
    df['PIN'] = df['PIN'].astype(str).str.strip()
    df['Kode_Area'] = df['Kode_Area'].astype(str).str.strip()
    df = df.sort_values(['PIN', 'Kode_Area', 'Waktu_Scan'])

    # 1. Pembersihan Double-Scan (< 1 jam di area sama)
    df['Prev_Scan'] = df.groupby(['PIN', 'Kode_Area'])['Waktu_Scan'].shift(1)
    df['Selisih_Jam'] = (df['Waktu_Scan'] - df['Prev_Scan']).dt.total_seconds() / 3600
    df = df[df['Selisih_Jam'].isna() | (df['Selisih_Jam'] >= 1.0)].copy()

    records = []
    for (pin, kode_area), group in df.groupby(['PIN', 'Kode_Area']):
        scans = group['Waktu_Scan'].tolist()
        areas = group['Kode_Area'].tolist()

        i = 0
        n = len(scans)
        while i < n:
            in_time = scans[i]
            in_area = areas[i]
            out_time = pd.NaT
            out_area = "-"

            if i + 1 < n:
                duration = (scans[i+1] - in_time).total_seconds() / 3600
                if duration <= 17:
                    out_time = scans[i+1]
                    out_area = areas[i+1]
                    i += 2
                else:
                    i += 1
            else:
                i += 1

            keterangan = "Normal"
            if pd.isna(out_time):
                keterangan = "Lupa Absen Keluar (Input Manual)"
            else:
                dur = (out_time - in_time).total_seconds() / 3600
                if dur > 9:
                    jam_l = int(dur - 8)
                    keterangan = f"Ada Lembur (+/- {jam_l} Jam)"

            kode_area_gabung = in_area
            if not pd.isna(out_time) and out_area != in_area and out_area != "-":
                kode_area_gabung = f"{in_area} / {out_area}"

            records.append({
                'PIN': pin,
                'Tanggal': in_time.date(),
                'Kode_Area': kode_area_gabung,
                'Jam_Masuk_Obj': in_time,
                'Jam_Keluar_Obj': out_time,
                'Total_Scan': 2 if not pd.isna(out_time) else 1,
                'Keterangan': keterangan
            })

    if not records:
        return pd.DataFrame()

    df_rekap = pd.DataFrame(records)

    # 2. Pemetaan Profil Divisi (Forming vs Umum)
    emp_dept_map = {}
    for pin_val, group in df_rekap.groupby('PIN'):
        pin_str = str(pin_val)
        times = group['Jam_Masuk_Obj'].dropna()
        if times.empty:
            emp_dept_map[pin_str] = 'UMUM'
            continue
        hours = times.dt.hour
        forming_count = ((hours == 6) | (hours == 7) | (hours == 14) | (hours == 15) | (hours == 22) | (hours == 23)).sum()
        ratio = forming_count / len(times)
        first_area = str(group['Kode_Area'].iloc[0])
        if ('Surabaya' in first_area or 'SF' in first_area) and ratio >= 0.35:
            emp_dept_map[pin_str] = 'FORMING'
        else:
            emp_dept_map[pin_str] = 'UMUM'

    # 3. Klasifikasi Shift secara Cepat
    shifts = []
    for _, row in df_rekap.iterrows():
        p = row['PIN']
        dept = emp_dept_map.get(p, 'UMUM')
        s_name = classifier.determine_shift(row['Jam_Masuk_Obj'], row['Kode_Area'], dept)
        shifts.append(s_name)
    df_rekap['Shift'] = shifts

    # 4. Format Jam ke String
    df_rekap['Jam_Masuk'] = df_rekap['Jam_Masuk_Obj'].dt.strftime('%H:%M:%S')
    df_rekap['Jam_Keluar'] = df_rekap['Jam_Keluar_Obj'].dt.strftime('%H:%M:%S').fillna("-")

    # 5. Mapping Metadata Karyawan
    akun_to_nama, akun_to_nip, df_kerja_unique = load_employee_metadata()
    df_rekap['Nama_Karyawan'] = df_rekap['PIN'].map(akun_to_nama).fillna("Karyawan " + df_rekap['PIN'])
    df_rekap['NIP_Asli'] = df_rekap['PIN'].map(akun_to_nip).fillna(df_rekap['PIN'])

    def map_area_str(kode_str):
        if not kode_str or pd.isna(kode_str):
            return "-"
        parts = [p.strip() for p in str(kode_str).split('/')]
        mapped = [DICT_AREA_NAMES.get(p, p) for p in parts]
        return " / ".join(mapped)

    df_rekap['Kode_Area'] = df_rekap['Kode_Area'].apply(map_area_str)

    if not df_kerja_unique.empty:
        df_rekap = pd.merge(df_rekap, df_kerja_unique, left_on='NIP_Asli', right_on='PIN', how='left', suffixes=('', '_kerja'))
        df_rekap['Lokasi_Kerja_Asli'] = df_rekap['Lokasi_Kerja_Asli'].fillna('Tidak Ditemukan')
        df_rekap['Kode_Jabatan'] = df_rekap['kd_jabatan'].fillna('-')
        df_rekap['Kode_Divisi'] = df_rekap['kd_divisi'].fillna('-')
    else:
        df_rekap['Lokasi_Kerja_Asli'] = 'Tidak Diketahui'
        df_rekap['Kode_Jabatan'] = '-'
        df_rekap['Kode_Divisi'] = '-'

    cols = [
        'PIN', 'Nama_Karyawan', 'Lokasi_Kerja_Asli', 'Kode_Jabatan', 'Kode_Divisi',
        'Tanggal', 'Kode_Area', 'Shift', 'Jam_Masuk', 'Jam_Keluar', 'Total_Scan', 'Keterangan'
    ]
    return df_rekap[cols]


def smart_merge_paired_data(existing_paired_path=PAIRED_FILE, new_paired_df=None):
    """
    Menggabungkan hasil pairing baru dengan dataset yang sudah ada:
    - Tidak menimpa baris yang sudah lengkap.
    - Tidak menduplikasi record yang identik.
    - Menambahkan baris untuk tanggal/scan baru.
    - Memperbarui baris jika sebelumnya 'Lupa Absen Keluar' dan kini ada jam pulangnya.
    """
    if new_paired_df is None or new_paired_df.empty:
        if os.path.exists(existing_paired_path):
            return pd.read_csv(existing_paired_path), 0, 0

    if not os.path.exists(existing_paired_path):
        new_paired_df.to_csv(existing_paired_path, index=False)
        return new_paired_df, len(new_paired_df), 0

    df_exist = pd.read_csv(existing_paired_path, dtype={'PIN': str})
    df_exist['PIN'] = df_exist['PIN'].astype(str).str.strip()
    df_exist['Tanggal'] = df_exist['Tanggal'].astype(str).str.strip()
    df_exist['Total_Scan'] = pd.to_numeric(df_exist['Total_Scan'], errors='coerce').fillna(1).astype(int)

    new_df = new_paired_df.copy()
    new_df['PIN'] = new_df['PIN'].astype(str).str.strip()
    new_df['Tanggal'] = new_df['Tanggal'].astype(str).str.strip()
    new_df['Total_Scan'] = pd.to_numeric(new_df['Total_Scan'], errors='coerce').fillna(1).astype(int)

    def norm_p(p):
        return str(p).strip().lstrip('0') or '0'

    exist_map = {}
    for idx, row in df_exist.iterrows():
        key = (norm_p(row['PIN']), str(row['Tanggal']), str(row['Jam_Masuk']))
        exist_map[key] = idx

    new_rows = []
    updated_count = 0

    for _, row in new_df.iterrows():
        key = (norm_p(row['PIN']), str(row['Tanggal']), str(row['Jam_Masuk']))
        if key in exist_map:
            exist_idx = exist_map[key]
            if df_exist.at[exist_idx, 'Total_Scan'] < row['Total_Scan']:
                for col in ['Jam_Keluar', 'Total_Scan', 'Keterangan', 'Shift', 'Kode_Area']:
                    df_exist.at[exist_idx, col] = row[col]
                updated_count += 1
        else:
            same_day_keys = [k for k in exist_map if k[0] == norm_p(row['PIN']) and k[1] == str(row['Tanggal'])]
            if same_day_keys and row['Total_Scan'] == 2 and any(df_exist.at[exist_map[k], 'Total_Scan'] == 1 for k in same_day_keys):
                target_k = [k for k in same_day_keys if df_exist.at[exist_map[k], 'Total_Scan'] == 1][0]
                exist_idx = exist_map[target_k]
                for col in ['Jam_Masuk', 'Jam_Keluar', 'Total_Scan', 'Keterangan', 'Shift', 'Kode_Area']:
                    df_exist.at[exist_idx, col] = row[col]
                updated_count += 1
            else:
                new_rows.append(row)

    if new_rows:
        df_new_add = pd.DataFrame(new_rows)
        df_final = pd.concat([df_exist, df_new_add], ignore_index=True)
    else:
        df_final = df_exist

    df_final = df_final.sort_values(['Tanggal', 'PIN'], ascending=[False, True])
    df_final.to_csv(existing_paired_path, index=False)

    return df_final, len(new_rows), updated_count


def process_uploaded_fingerprint(file_obj, filename, default_area='SF'):
    """
    Fungsi all-in-one yang dipanggil saat user meng-upload file log fingerprint di aplikasi:
    1. Parse file menjadi DataFrame scan mentah.
    2. Simpan dan deduplikasi ke Raw_Logs.csv.
    3. Pairing log yang bersangkutan.
    4. Smart merge ke Hasil_Pairing_Absensi_Dengan_Shift_Revisi.csv tanpa menimpa/menumpuk data lama.
    5. Mengembalikan ringkasan statistik proses.
    """
    new_raw_df = parse_fingerprint_file(file_obj, filename, default_area=default_area)

    all_raw_df, total_scans, new_scans, dups_skipped = ingest_raw_logs(new_raw_df)

    classifier = ShiftClassifier()
    if new_scans > 0:
        affected_pins = set(new_raw_df['PIN'].unique())
        df_to_pair = all_raw_df[all_raw_df['PIN'].isin(affected_pins)].copy()

        # [OPTIMASI] Filter raw logs untuk mempercepat proses pairing
        # Hanya mengevaluasi data dari H-2 tanggal pairing terakhir
        # (menggunakan H-2 alih-alih H-1 untuk mengamankan data Shift 3 / lintas hari)
        if os.path.exists(PAIRED_FILE):
            try:
                df_paired = pd.read_csv(PAIRED_FILE, usecols=['Tanggal'])
                if not df_paired.empty:
                    max_date_str = df_paired['Tanggal'].max()
                    max_date_obj = pd.to_datetime(max_date_str)
                    threshold_date = (max_date_obj - datetime.timedelta(days=2)).strftime('%Y-%m-%d')
                    df_to_pair = df_to_pair[df_to_pair['Waktu_Scan'] >= threshold_date].copy()
            except Exception:
                pass

        paired_new = run_pairing_process(df_to_pair, classifier=classifier)

        df_final, added_records, updated_records = smart_merge_paired_data(
            existing_paired_path=PAIRED_FILE,
            new_paired_df=paired_new
        )
    else:
        if os.path.exists(PAIRED_FILE):
            df_final = pd.read_csv(PAIRED_FILE)
        else:
            df_final = pd.DataFrame()
        added_records = 0
        updated_records = 0

    date_min = new_raw_df['Waktu_Scan'].min()[:10] if not new_raw_df.empty else "-"
    date_max = new_raw_df['Waktu_Scan'].max()[:10] if not new_raw_df.empty else "-"

    return {
        'total_scans_in_file': total_scans,
        'new_scans_added': new_scans,
        'duplicates_skipped': dups_skipped,
        'added_paired_records': added_records,
        'updated_paired_records': updated_records,
        'date_min': date_min,
        'date_max': date_max,
        'total_rows_now': len(df_final)
    }
