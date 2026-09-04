import pandas as pd
import re

filepath = 't_absensi_solutions_fp.sql'
data = []
pattern = re.compile(r"\('([^']*)',\s*'([^']*)',\s*'([^']*)',\s*(\d+),\s*'([^']*)'\)")
with open(filepath, 'r', encoding='utf-8') as file:
    for line in file:
        if line.strip().startswith("('"):
            matches = pattern.findall(line)
            for match in matches:
                kode_area = match[0]
                pin = match[1]
                waktu_scan = match[2]
                if pin == '206705':
                    data.append({
                        'Kode_Area': kode_area,
                        'PIN': pin, 
                        'Waktu_Scan': waktu_scan
                    })
df = pd.DataFrame(data)
df['Waktu_Scan'] = pd.to_datetime(df['Waktu_Scan'])
df = df.sort_values(['PIN', 'Waktu_Scan'])
print("Raw:")
print(df[df['Waktu_Scan'].dt.date == pd.to_datetime('2026-08-01').date()])

df['Prev_Scan'] = df.groupby('PIN')['Waktu_Scan'].shift(1)
df['Selisih_Jam'] = (df['Waktu_Scan'] - df['Prev_Scan']).dt.total_seconds() / 3600
print("\nBefore filter:")
print(df[df['Waktu_Scan'].dt.date == pd.to_datetime('2026-08-01').date()])

df = df[df['Selisih_Jam'].isna() | (df['Selisih_Jam'] >= 1.0)].copy()
print("\nAfter filter:")
print(df[df['Waktu_Scan'].dt.date == pd.to_datetime('2026-08-01').date()])
