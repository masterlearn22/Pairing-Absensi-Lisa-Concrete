import pandas as pd

df = pd.read_csv('Hasil_Pairing_Absensi_Dengan_Shift_Revisi.csv')
df['Tanggal'] = pd.to_datetime(df['Tanggal'])

# Filter rentang tanggal
start_date = pd.to_datetime('2026-08-21')
end_date = pd.to_datetime('2026-08-31')
mask = (df['Tanggal'] >= start_date) & (df['Tanggal'] <= end_date)
df_filtered = df.loc[mask]

# Cari anomali (Keterangan tidak sama dengan 'Normal')
anomalies = df_filtered[df_filtered['Keterangan'] != 'Normal']

print(f"Total data di rentang {start_date.date()} s/d {end_date.date()}: {len(df_filtered)}")
print(f"Total anomali ditemukan: {len(anomalies)}")
print("\nSebaran jenis anomali:")
print(anomalies['Keterangan'].value_counts())

# Tampilkan beberapa contoh Lupa Absen
print("\nContoh Kasus Lupa Absen Keluar (Input Manual):")
lupa = anomalies[anomalies['Keterangan'].str.contains('Lupa', na=False)]
if not lupa.empty:
    print(lupa[['PIN', 'Nama_Karyawan', 'Tanggal', 'Jam_Masuk', 'Jam_Keluar']].head(5))

# Tampilkan beberapa contoh Lembur ekstrim
print("\nContoh Kasus Lembur Besar (> 4 Jam):")
lembur_ekstrim = anomalies[anomalies['Keterangan'].str.contains('\+/\- [5-9]', na=False)]
if not lembur_ekstrim.empty:
    print(lembur_ekstrim[['PIN', 'Nama_Karyawan', 'Tanggal', 'Jam_Masuk', 'Jam_Keluar', 'Keterangan']].head(5))
