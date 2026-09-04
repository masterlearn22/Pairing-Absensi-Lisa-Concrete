import pandas as pd
import re

def parse_kerja_sql(filepath):
    print(f"Membaca file {filepath}...")
    data = []
    
    # Pattern to match INSERT INTO `tdt_kerja` ... VALUES ('LCI', '01', '01', '04', '42', '00', '00', '100182', '2012-09-24', NULL)
    # Some values are NULL, some are strings.
    # Let's use a robust regex or just split by comma.
    
    pattern = re.compile(r"\((.*?)\)")
    
    try:
        with open(filepath, 'r', encoding='utf-8') as file:
            for line in file:
                if line.strip().startswith("("):
                    matches = pattern.findall(line)
                    for match in matches:
                        # match is a string like: 'LCI', '01', '01', '04', '42', '00', '00', '100182', '2012-09-24', NULL
                        # Split by comma, but be careful with quotes.
                        # Since all are simple strings without commas inside, we can just split by comma and clean up.
                        parts = [p.strip().strip("'") for p in match.split(',')]
                        if len(parts) >= 10:
                            data.append({
                                'kd_gol_kary': parts[0],
                                'kd_sts_kary': parts[1],
                                'kd_lok_krj': parts[2],
                                'kd_jabatan': parts[3],
                                'kd_divisi': parts[4],
                                'kd_divisi_bag': parts[5],
                                'kd_divisi_sub_bag': parts[6],
                                'PIN': parts[7], # nip = PIN
                                'tgl_msk': parts[8] if parts[8] != 'NULL' else None,
                                'tgl_klr': parts[9] if parts[9] != 'NULL' else None
                            })
    except Exception as e:
        print(f"Gagal membaca {filepath}: {e}")
        
    df = pd.DataFrame(data)
    
    # Mapping Kode Lokasi
    map_lokasi = {
        '01': 'Surabaya Office (SO)',
        '02': 'Bali Office (BO)',
        '03': 'Surabaya Factory (SF)',
        '04': 'Bali Factory (BF)'
    }
    if not df.empty:
        df['Lokasi_Kerja_Asli'] = df['kd_lok_krj'].map(lambda x: map_lokasi.get(x, x))
    
    return df

if __name__ == "__main__":
    df_kerja = parse_kerja_sql('t_dt_krj.sql')
    if not df_kerja.empty:
        df_kerja.to_csv('Data_Kerja.csv', index=False)
        print(f"Berhasil mengekstrak {len(df_kerja)} data karyawan ke Data_Kerja.csv")
    else:
        print("Data kerja kosong atau gagal di-parse.")
