import pandas as pd
import re
import os

def parse_shift_sql(filepath):
    print(f"Membaca file {filepath}...")
    data = []
    
    # \d+ for ID, string for others. 
    # Example line: (2, '03', 'SHIFT PAGI SF', '08:00', '16:00', '2023-01-31 13:54:58'),
    pattern = re.compile(r"\((\d+),\s*'([^']*)',\s*'([^']*)',\s*'([^']*)',\s*'([^']*)',\s*'([^']*)'\)")
    
    try:
        with open(filepath, 'r', encoding='utf-8') as file:
            for line in file:
                # Value lines start with ( or whitespace (
                if line.strip().startswith("("):
                    matches = pattern.findall(line)
                    for match in matches:
                        data.append({
                            'IDSKK': match[0],
                            'kd_lok_krj': match[1],
                            'shiftkrj': match[2],
                            'JAT': match[3],
                            'JST': match[4],
                            'tglinput': match[5]
                        })
    except Exception as e:
        print(f"Gagal membaca {filepath}: {e}")
        
    df = pd.DataFrame(data)
    
    # Mapping Kode Lokasi ke Area (seperti di absensi)
    # '01'(HO), '02'(BO), '03'(SF), '04'(BF)
    map_lokasi = {
        '01': 'SO', # Asumsi HO = SO (Surabaya Office)
        '02': 'BO',
        '03': 'SF',
        '04': 'BF',
        '': 'ALL' # Jika kosong, berlaku untuk semua
    }
    
    if not df.empty:
        df['Area'] = df['kd_lok_krj'].map(lambda x: map_lokasi.get(x, x))
    
    return df

if __name__ == "__main__":
    df_shift = parse_shift_sql('t_mst_shift_krj.sql')
    if not df_shift.empty:
        df_shift.to_csv('Data_Shift.csv', index=False)
        print(f"Berhasil mengekstrak {len(df_shift)} data shift ke Data_Shift.csv")
    else:
        print("Data shift kosong atau gagal di-parse.")
