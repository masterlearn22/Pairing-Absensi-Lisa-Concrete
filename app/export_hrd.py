import pandas as pd
import datetime

def time_to_min(t_str):
    if not t_str or str(t_str).strip() == '-' or pd.isna(t_str):
        return None
    try:
        parts = str(t_str).split(':')
        return int(parts[0]) * 60 + int(parts[1])
    except Exception:
        return None

def min_to_time(m):
    if m is None or pd.isna(m):
        return ""
    m = max(0, int(m))
    h = m // 60
    mn = m % 60
    return f"{h:02d}:{mn:02d}"

def generate_export_hrd(df_paired, start_date, end_date):
    """
    Menghasilkan format output persis seperti struktur tabel t_absensi_solutions_harian
    (Sesuai arahan Pak Heru: fokus ke data pairing dasar).
    Kolom: area, pin, tgl_absensi, tanggal, jam_masuk, jam_pulang, durasi_jam, total_scan, confidence
    """
    rows = []
    hari_map = {0: 'Senin', 1: 'Selasa', 2: 'Rabu', 3: 'Kamis', 4: 'Jumat', 5: 'Sabtu', 6: 'Minggu'}
    
    # Filter data berdasarkan rentang tanggal
    # (Opsional jika df_paired sudah difilter dari luar, tapi untuk jaga-jaga kita iterasi semua)
    for _, r in df_paired.iterrows():
        area_str = str(r.get('Kode_Area', ''))
        # Jika ada multi area (misal SF / BF), ambil yang pertama
        area = area_str.split(' / ')[0].strip()
        if area == 'Surabaya Factory': area = 'SF'
        elif area == 'Bali Factory': area = 'BF'
        elif area == 'Surabaya Office': area = 'SO'
        elif area == 'Bali Office': area = 'BO'
            
        pin = str(r['PIN']).strip()
        tgl_absensi = str(r['Tanggal']).strip()
        tanggal = tgl_absensi # Sama dengan tgl_absensi
        
        jam_masuk = str(r.get('Jam_Masuk', r.get('Waktu_Masuk', '')))
        jam_pulang = str(r.get('Jam_Keluar', r.get('Waktu_Keluar', '')))
        
        if pd.isna(jam_masuk) or jam_masuk == '-': jam_masuk = ""
        if pd.isna(jam_pulang) or jam_pulang == '-': jam_pulang = ""
        
        durasi_jam = 0.00
        confidence = 100
        
        if jam_masuk and jam_pulang:
            try:
                # Gabungkan tanggal dan jam agar parsing harinya akurat
                dt_in = pd.to_datetime(f"{tgl_absensi} {jam_masuk}")
                
                # Jika jam pulang lebih kecil dari jam masuk, asumsikan lewat tengah malam (hari berikutnya)
                dt_out_temp = pd.to_datetime(f"{tgl_absensi} {jam_pulang}")
                if dt_out_temp < dt_in:
                    dt_out_temp += pd.Timedelta(days=1)
                dt_out = dt_out_temp
                
                durasi_sec = (dt_out - dt_in).total_seconds()
                durasi_jam = round(durasi_sec / 3600.0, 2)
                
                hari_in = hari_map[dt_in.weekday()]
                hari_out = hari_map[dt_out.weekday()]
                jam_masuk = f"{hari_in}, {jam_masuk}"
                jam_pulang = f"{hari_out}, {jam_pulang}"
            except Exception:
                pass
        elif jam_masuk:
            try:
                dt_in = pd.to_datetime(f"{tgl_absensi} {jam_masuk}")
                jam_masuk = f"{hari_map[dt_in.weekday()]}, {jam_masuk}"
            except Exception:
                pass
            confidence = 20
        else:
            # Jika bolong
            confidence = 20

        try:
            dt_tgl = pd.to_datetime(tgl_absensi)
            tgl_str = f"{hari_map[dt_tgl.weekday()]}, {tgl_absensi}"
            tgl_absensi = tgl_str
            tanggal = tgl_str
        except Exception:
            pass

        total_scan = 1
        try:
            total_scan = int(r.get('Total_Scan', 1))
        except Exception:
            pass
            
        rows.append({
            'area': area,
            'pin': pin,
            'tgl_absensi': tgl_absensi,
            'tanggal': tanggal,
            'jam_masuk': jam_masuk if jam_masuk else "NULL",
            'jam_pulang': jam_pulang if jam_pulang else "NULL",
            'durasi_jam': durasi_jam,
            'total_scan': total_scan,
            'confidence': confidence
        })
                
    return pd.DataFrame(rows)
