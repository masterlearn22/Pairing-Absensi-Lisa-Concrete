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
    df_paired: DataFrame dari Hasil_Pairing_Absensi_Dengan_Shift_Revisi.csv
    start_date, end_date: datetime.date
    """
    hari_map = {0: 'Senin', 1: 'Selasa', 2: 'Rabu', 3: 'Kamis', 4: 'Jumat', 5: 'Sabtu', 6: 'Minggu'}
    
    # Ambil daftar unik karyawan
    karyawan_list = df_paired[['PIN', 'Nama_Karyawan', 'Lokasi_Kerja_Asli']].drop_duplicates(subset=['PIN'])
    
    # Dictionary mapping PIN + Tanggal -> baris absensi
    absen_dict = {}
    for _, r in df_paired.iterrows():
        key = (str(r['PIN']).strip(), str(r['Tanggal']).strip())
        if key not in absen_dict:
            absen_dict[key] = r
            
    rows = []
    
    # Buat rentang tanggal full
    date_range = [start_date + datetime.timedelta(days=x) for x in range((end_date - start_date).days + 1)]
    
    for _, k in karyawan_list.iterrows():
        pin = str(k['PIN']).strip()
        nama = str(k['Nama_Karyawan'])
        
        for d in date_range:
            d_str = d.strftime('%Y-%m-%d')
            hari = hari_map[d.weekday()]
            ttgs = d.strftime('%d/%m/%Y')
            
            key = (pin, d_str)
            if key in absen_dict:
                r = absen_dict[key]
                
                # Coba parse shift
                shift_str = str(r['Shift'])
                jtgs = ""
                jsls = ""
                if "(" in shift_str and "-" in shift_str:
                    try:
                        times = shift_str.split("(")[1].replace(")", "").split("-")
                        if len(times) == 2:
                            jtgs = times[0].strip()
                            jsls = times[1].strip()
                    except Exception:
                        pass
                
                if not jtgs: jtgs = "08:00"
                if not jsls: jsls = "16:00"
                
                jdtg = str(r['Jam_Masuk'])[:5] if pd.notna(r['Jam_Masuk']) and str(r['Jam_Masuk']) != '-' else ""
                jplg = str(r['Jam_Keluar'])[:5] if pd.notna(r['Jam_Keluar']) and str(r['Jam_Keluar']) != '-' else ""
                
                min_jtgs = time_to_min(jtgs)
                min_jsls = time_to_min(jsls)
                if min_jsls is not None and min_jtgs is not None and min_jsls < min_jtgs:
                    min_jsls += 24 * 60
                    
                min_jdtg = time_to_min(jdtg)
                min_jplg = time_to_min(jplg)
                if min_jplg is not None and min_jdtg is not None and min_jplg < min_jdtg:
                    min_jplg += 24 * 60
                
                # JJK
                jjk = ""
                if min_jdtg is not None and min_jplg is not None:
                    diff = min_jplg - min_jdtg
                    jjk = f"({min_to_time(diff)})"
                    
                tlmbt = 0
                plgawal = 0
                dtgaw = ""
                plgak = ""
                jml_lmbr = 0
                unit_lmbr = "0"
                
                if min_jdtg is not None and min_jtgs is not None:
                    if min_jdtg > min_jtgs:
                        tlmbt = min_jdtg - min_jtgs
                    elif min_jdtg < min_jtgs:
                        dtgaw = min_to_time(min_jtgs - min_jdtg)
                        
                if min_jplg is not None and min_jsls is not None:
                    if min_jplg < min_jsls:
                        plgawal = min_jsls - min_jplg
                    elif min_jplg > min_jsls:
                        diff_plgak = min_jplg - min_jsls
                        plgak = min_to_time(diff_plgak)
                        jml_lmbr = diff_plgak // 60
                        
                if jml_lmbr > 0:
                    unit = 1.5 + (jml_lmbr - 1) * 2.0 if jml_lmbr > 1 else 1.5
                    unit_lmbr = str(unit).replace('.', ',')
                    
                spkl = "Tdk. Ada SPKL"
                if jml_lmbr > 0:
                    spkl = f"{pin}{d.strftime('%d%m%Y')}{jsls.replace(':', '')}"
                    
                catatan = ""
                stsdate = "OK"
                if not jplg:
                    catatan = "Lupa absen pulang"
                    stsdate = "NOT OK"
                if not jdtg and not jplg:
                    catatan = "-NONE-"
                    stsdate = "NOT OK"
                    
                rows.append({
                    'Nip': pin,
                    'Nama': nama,
                    'Hari': hari,
                    'TTgs': ttgs,
                    'JTgs': jtgs,
                    'JSlS': jsls,
                    'TDtg': ttgs,
                    'JDtg': jdtg,
                    'JPlg': jplg,
                    'JJK': jjk,
                    'Tlmbt': tlmbt,
                    'PlgAwal': plgawal,
                    'SPKL': spkl,
                    'JmlLmbr': jml_lmbr,
                    'UnitLmbr': unit_lmbr,
                    'PJL': 0,
                    'DtgAw': dtgaw,
                    'PlgAk': plgak,
                    'Catatan': catatan,
                    'Stsdate': stsdate
                })
            else:
                # Bolong / Tidak ada data
                rows.append({
                    'Nip': pin,
                    'Nama': nama,
                    'Hari': hari,
                    'TTgs': ttgs,
                    'JTgs': "",
                    'JSlS': "",
                    'TDtg': "",
                    'JDtg': "",
                    'JPlg': "",
                    'JJK': "",
                    'Tlmbt': 0,
                    'PlgAwal': 0,
                    'SPKL': "Tdk. Ada SPKL",
                    'JmlLmbr': 0,
                    'UnitLmbr': 0,
                    'PJL': 0,
                    'DtgAw': "",
                    'PlgAk': "",
                    'Catatan': "-NONE-",
                    'Stsdate': "NOT OK"
                })
                
    return pd.DataFrame(rows)
