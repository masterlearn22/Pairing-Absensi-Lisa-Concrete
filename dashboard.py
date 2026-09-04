import streamlit as st
import pandas as pd
import os
from datetime import datetime
import pairing_engine


def load_data():
    file_path = "Hasil_Pairing_Absensi_Dengan_Shift_Revisi.csv"
    if not os.path.exists(file_path):
        return pd.DataFrame()
    df = pd.read_csv(file_path)
    df['PIN'] = df['PIN'].astype(str)
    return df


@st.cache_data
def load_shift_data():
    file_path = "Data_Shift.csv"
    if not os.path.exists(file_path):
        return pd.DataFrame()
    df = pd.read_csv(file_path)
    return df


@st.cache_data
def load_boss_data():
    import re
    boss_data = []
    pattern = re.compile(
        r"\('([^']*)',\s*'([^']*)',\s*'([^']*)',\s*'([^']*)',\s*'([^']*)',\s*'([^']*)',\s*([^,]+),\s*([^,]+),\s*([^)]+)\)")
    filepath = 't_absensi_solutions_harian.sql'
    if not os.path.exists(filepath):
        return pd.DataFrame()

    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            for line in f:
                if line.strip().startswith("('"):
                    for match in pattern.findall(line):
                        boss_data.append({
                            'Kode_Area': match[0],
                            'PIN': match[1],
                            'Tanggal': match[2],
                            'Jam_Masuk_Atasan': match[4],
                            'Jam_Keluar_Atasan': match[5],
                            'Total_Jam_Kerja': float(match[6])
                        })
    except Exception:
        pass
    return pd.DataFrame(boss_data)


@st.cache_data
def load_raw_data():
    if os.path.exists('Raw_Logs.csv'):
        try:
            df_raw = pd.read_csv('Raw_Logs.csv')
            df_raw['PIN'] = df_raw['PIN'].astype(str)
            df_raw['Log_Time'] = pd.to_datetime(df_raw['Waktu_Scan'], errors='coerce')
            df_raw['Status'] = df_raw['Status'].apply(lambda x: "Keluar (OUT)" if str(x) == "1" else "Masuk (IN)")
            if not df_raw.empty:
                return df_raw.sort_values(by=['PIN', 'Log_Time'])
        except Exception:
            pass

    import re
    raw_data = []
    pattern = re.compile(
        r"\('([^']*)',\s*'([^']*)',\s*'([^']*)',\s*(\d+),\s*'([^']*)'\)")
    filepath = 't_absensi_solutions_fp.sql'
    if not os.path.exists(filepath):
        return pd.DataFrame()

    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            for line in f:
                if line.strip().startswith("('"):
                    for match in pattern.findall(line):
                        raw_data.append({
                            'Kode_Area': match[0],
                            'PIN': match[1],
                            'Waktu_Scan': match[2],
                            'Status': "Keluar (OUT)" if match[3] == "1" else "Masuk (IN)",
                            'Log_Time': pd.to_datetime(match[2])
                        })
    except Exception:
        pass
    df_raw = pd.DataFrame(raw_data)
    if not df_raw.empty:
        df_raw = df_raw.sort_values(by=['PIN', 'Log_Time'])
    return df_raw


def hitung_lembur_row(row):
    try:
        if pd.isna(row['Jam_Keluar']) or row['Jam_Keluar'] == '-' or pd.isna(row['Jam_Masuk']) or row['Jam_Masuk'] == '-':
            return "-"

        jam_keluar_str = str(row['Jam_Keluar'])
        jam_masuk_str = str(row['Jam_Masuk'])

        # Ekstrak jam dan menit
        h_out, m_out, _ = map(int, jam_keluar_str.split(':'))
        h_in, m_in, _ = map(int, jam_masuk_str.split(':'))

        total_menit_in = h_in * 60 + m_in
        total_menit_out = h_out * 60 + m_out

        # Jika lintas hari (Shift 3 atau lembur sampai besok)
        if total_menit_out < total_menit_in:
            total_menit_out += 24 * 60

        durasi_kerja_menit = total_menit_out - total_menit_in

        shift = str(row['Shift'])
        tanggal_date = row['Tanggal_Date']
        is_saturday = (tanggal_date.weekday() == 5)

        # Jam kerja standar adalah 8 jam (480 menit)
        batas_kerja_menit = 8 * 60
        # Khusus Sabtu Shift 1, jam kerja normal 5 jam (08:00 - 13:00)
        if "Shift 1" in shift and is_saturday:
            batas_kerja_menit = 5 * 60

        selisih = durasi_kerja_menit - batas_kerja_menit

        # Jika total jam kerja lebih besar dari jam kerja standar, maka dihitung lembur
        if selisih > 0:
            jam = selisih // 60
            menit = selisih % 60
            if jam == 0:
                return f"0 jam {menit} mnt"
            return f"{jam} jam {menit} mnt"

        return "-"
    except Exception as e:
        return "-"


def main():
    st.set_page_config(layout="wide", page_title="Dashboard Absensi & Shift")

    st.title("📊 Sistem Terpadu Absensi & Shift Kerja")
    st.write(
        "Mengelola riwayat absensi karyawan dan referensi shift kerja yang dinamis.")

    tab1, tab_upload, tab2 = st.tabs(["📊 Dashboard Kehadiran", "📤 Upload & Pairing Log Finger", "🏢 Master Data Shift"])

    with tab2:
        st.header("🏢 Master Data Shift Kerja")
        df_shift = load_shift_data()
        if df_shift.empty:
            st.warning(
                "Data Master Shift kosong. Pastikan Data_Shift.csv tersedia.")
        else:
            st.dataframe(df_shift, use_container_width=True)

    with tab_upload:
        st.header("📤 Upload & Sinkronisasi Log Mesin Fingerprint")
        st.write(
            "Unggah data log dari mesin absensi untuk otomatis dipasangkan (pairing jam masuk, jam keluar, shift kerja, dan lembur). "
            "Sistem **tidak akan menimpa (overwrite)** data lama dan **tidak akan menduplikasi** data yang sama, melainkan menambahkan scan baru secara incremental."
        )

        # Statistik Data Saat Ini
        c_stat1, c_stat2, c_stat3 = st.columns(3)
        total_raw = 0
        if os.path.exists("Raw_Logs.csv"):
            try:
                df_rl = pd.read_csv("Raw_Logs.csv")
                total_raw = len(df_rl)
            except Exception:
                pass
        df_paired_curr = load_data()
        total_paired = len(df_paired_curr) if not df_paired_curr.empty else 0
        total_karyawan_curr = df_paired_curr['PIN'].nunique() if not df_paired_curr.empty else 0

        c_stat1.metric("📦 Total Log Mentah Tersimpan", f"{total_raw:,} scan")
        c_stat2.metric("📋 Total Rekap Absensi Ter-pairing", f"{total_paired:,} baris")
        c_stat3.metric("👥 Total Karyawan Aktif Terdata", f"{total_karyawan_curr:,} orang")

        st.divider()

        col_up1, col_up2 = st.columns([2, 1])

        with col_up1:
            uploaded_file = st.file_uploader(
                "Pilih File Log Mesin Fingerprint:",
                type=["csv", "xlsx", "xls", "sql", "txt", "dat"],
                help="Mendukung format SQL dump, Excel (.xlsx/.xls), CSV (.csv), dan file USB flashdisk (.dat/.txt seperti attlog.dat)"
            )

        with col_up2:
            default_area = st.selectbox(
                "Default Lokasi/Pabrik (jika di file log tidak ada kolom area):",
                options=["Surabaya Factory (SF)", "Bali Factory (BF)", "Surabaya Office (SO)", "Bali Office (BO)"],
                index=0
            )
            area_code_map = {
                "Surabaya Factory (SF)": "SF",
                "Bali Factory (BF)": "BF",
                "Surabaya Office (SO)": "SO",
                "Bali Office (BO)": "BO"
            }
            chosen_area_code = area_code_map.get(default_area, "SF")

        if uploaded_file is not None:
            st.info(f"📄 File dipilih: **{uploaded_file.name}** ({uploaded_file.size / 1024:.1f} KB)")

            try:
                uploaded_file.seek(0)
                preview_raw = pairing_engine.parse_fingerprint_file(
                    uploaded_file, uploaded_file.name, default_area=chosen_area_code
                )
                uploaded_file.seek(0)

                st.subheader("🔍 Preview Log Scan yang Terdeteksi")
                st.write(f"Ditemukan **{len(preview_raw):,} log scan** dalam file ini:")
                st.dataframe(preview_raw.head(8), use_container_width=True)

                btn_proses = st.button("⚡ Mulai Pairing & Sinkronkan ke Sistem", type="primary", use_container_width=True)

                if btn_proses:
                    with st.spinner("Sedang memproses log, mengecek anti-duplikasi, dan memasangkan shift..."):
                        uploaded_file.seek(0)
                        result = pairing_engine.process_uploaded_fingerprint(
                            uploaded_file, uploaded_file.name, default_area=chosen_area_code
                        )
                        st.cache_data.clear()

                    st.success("✅ Log Fingerprint Berhasil Diproses & Disinkronkan!")

                    m_col1, m_col2, m_col3, m_col4 = st.columns(4)
                    m_col1.metric("📥 Total Log di File", f"{result['total_scans_in_file']:,}")
                    m_col2.metric("✨ Log Baru Ditambahkan", f"{result['new_scans_added']:,}")
                    m_col3.metric("🛡️ Duplikat Dilewati (Anti-Tumpang)", f"{result['duplicates_skipped']:,}")
                    m_col4.metric("📋 Rekap Baru/Diperbarui", f"{result['added_paired_records'] + result['updated_paired_records']:,}")

                    st.info(
                        f"📅 **Rentang Tanggal Log:** {result['date_min']} s/d {result['date_max']} | "
                        f"**Total Baris Hasil Pairing Sekarang:** {result['total_rows_now']:,} baris."
                    )

                    st.balloons()

                    st.markdown("""
                    > **Status Sinkronisasi:**
                    > - Seluruh scan baru telah otomatis ter-pairing dengan shift kerja dan jam lembur.
                    > - Data lama **tidak tertimpa** dan data scan identik **tidak menumpuk/dobel**.
                    > - Jika ada karyawan yang sebelumnya tercatat *Lupa Absen Keluar* dan di file ini terdapat scan pulangnya, statusnya otomatis disempurnakan.
                    > - Buka tab **'📊 Dashboard Kehadiran'** untuk langsung memfilter dan menganalisis rekap terbaru!
                    """)

            except Exception as e:
                st.error(f"❌ Gagal memproses file: {str(e)}")

        with st.expander("ℹ️ Panduan Format File yang Didukung"):
            st.markdown("""
            Sistem ini fleksibel dan mendukung berbagai format output mesin absensi:
            1. **Format Excel (.xlsx, .xls)**: Ekspor dari aplikasi Solution, Fingerspot, atau ZKBioSecurity. Nama kolom otomatis diselaraskan (PIN/NIP/User ID dan Tanggal/Waktu Scan).
            2. **Format CSV (.csv)**: Pemisah koma (`,`), titik-koma (`;`), atau tab (`\\t`).
            3. **Format USB Flashdisk (.dat / .txt)**: File `attlog.dat` yang langsung ditarik dari slot USB mesin absensi.
            4. **Format SQL Dump (.sql)**: Query `INSERT INTO` tabel absensi mesin.
            """)

    with tab1:
        df = load_data()

        if df.empty:
            st.warning(
                "Data absensi belum tersedia. Silakan jalankan script `pairing_data_revisi.py` terlebih dahulu.")
            st.stop()

        # Konversi string tanggal ke datetime.date agar bisa dibandingkan dan dipakai
        if not pd.api.types.is_datetime64_any_dtype(df['Tanggal']):
            df['Tanggal_Date'] = pd.to_datetime(df['Tanggal']).dt.date
        else:
            df['Tanggal_Date'] = df['Tanggal'].dt.date

        df['Jam Lembur'] = df.apply(hitung_lembur_row, axis=1)

        st.divider()
        st.header("📅 Filter Rentang Tanggal")

        min_date = df['Tanggal_Date'].min()
        max_date = df['Tanggal_Date'].max()

        # Default rentang: 21-20 (Siklus Kerja Lisa Concrete Indonesia)
        import datetime
        
        if max_date.day <= 20:
            # Periode: 21 bulan lalu s/d 20 bulan ini
            if max_date.month == 1:
                default_start = datetime.date(max_date.year - 1, 12, 21)
            else:
                default_start = datetime.date(max_date.year, max_date.month - 1, 21)
            default_end = datetime.date(max_date.year, max_date.month, 20)
        else:
            # Periode: 21 bulan ini s/d 20 bulan depan
            default_start = datetime.date(max_date.year, max_date.month, 21)
            if max_date.month == 12:
                default_end = datetime.date(max_date.year + 1, 1, 20)
            else:
                default_end = datetime.date(max_date.year, max_date.month + 1, 20)
                
        # Mencegah error Streamlit jika default di luar rentang min_date atau max_date
        default_start = max(default_start, min_date)
        default_end = min(default_end, max_date)
        
        # Pastikan start <= end
        if default_start > default_end:
            default_start = default_end

        col_filter, _ = st.columns([1, 2])
        with col_filter:
            date_range = st.date_input(
                "Mulai dari - Sampai dengan:",
                value=(default_start, default_end),
                min_value=min_date,
                max_value=max_date
            )

        if len(date_range) == 2:
            start_date, end_date = date_range
            # Saring data yang hanya berada dalam rentang tanggal tersebut
            df = df[(df['Tanggal_Date'] >= start_date)
                    & (df['Tanggal_Date'] <= end_date)]
            
            # --- EKSPOR HRD ---
            import export_hrd
            
            @st.cache_data(show_spinner=False)
            def get_export_csv(df_to_export, s_date, e_date):
                df_exp = export_hrd.generate_export_hrd(df_to_export, s_date, e_date)
                cols = ['Nip', 'Nama', 'Hari', 'TTgs', 'JTgs', 'JSlS', 'TDtg', 'JDtg', 'JPlg', 'JJK', 'Tlmbt', 'PlgAwal', 'SPKL', 'JmlLmbr', 'UnitLmbr', 'PJL', 'DtgAw', 'PlgAk', 'Catatan', 'Stsdate']
                return df_exp[cols].to_csv(index=False, sep=';').encode('utf-8')
            
            csv_data = get_export_csv(df, start_date, end_date)
            
            c_exp, c_info = st.columns([1, 2])
            with c_exp:
                st.download_button(
                    label="📥 Ekspor ke Format HRD",
                    data=csv_data,
                    file_name=f"Export_HRD_{start_date}_to_{end_date}.csv",
                    mime="text/csv",
                    type="primary"
                )
            with c_info:
                st.caption("Menghasilkan file CSV siap impor ke software HRD/Payroll lama (termasuk deteksi lembur dan *missing days*).")

        else:
            # Jika user baru mengklik 1 tanggal, kita tunggu
            st.info("Silakan pilih tanggal awal dan tanggal akhir.")

        st.divider()

        st.header("Ringkasan Absensi per Karyawan")

        # Calculate summary
        summary = df.groupby(['PIN', 'Nama_Karyawan']).agg(
            Total_Hari_Hadir=('Tanggal', 'nunique'),
            Total_Scan=('Total_Scan', 'sum')
        ).reset_index()

        summary = summary.sort_values(by='Total_Hari_Hadir', ascending=False)
        summary.rename(
            columns={'Total_Hari_Hadir': 'Total Kehadiran (Hari)'}, inplace=True)

        # Tata letak kolom
        col1, col2 = st.columns([1.2, 2])

        with col1:
            st.subheader("Daftar Karyawan")

            # Tampilkan total karyawan yang absen
            total_karyawan = summary['PIN'].nunique()
            st.info(
                f"👥 Terdapat **{total_karyawan} karyawan** yang memiliki riwayat absen pada rentang tanggal ini.")

            # Buat dictionary untuk selectbox (Pin -> Text)
            pin_to_name = {row['PIN']: str(row['Nama_Karyawan'])
                           for _, row in summary.iterrows()}

            st.write(
                "**Tabel Ringkasan (💡 Klik baris mana saja untuk melihat detail)**")
            event = st.dataframe(
                summary,
                use_container_width=True,
                hide_index=True,
                on_select="rerun",
                selection_mode="single-row"
            )

            # Cek apakah ada baris yang dipilih dari tabel
            selected_rows = event.selection.rows
            default_idx = selected_rows[0] if selected_rows else 0

            selected_pin = st.selectbox(
                "Atau cari nama di kotak ini:",
                options=summary['PIN'].tolist(),
                index=default_idx,
                format_func=lambda x: pin_to_name.get(x, x)
            )

        with col2:
            if selected_pin:
                selected_name = summary.loc[summary['PIN']
                                            == selected_pin, 'Nama_Karyawan'].values[0]
                st.subheader(f"Detail Absensi: {selected_name}")

                # Filter data khusus karyawan ini
                df_detail = df[df['PIN'] == selected_pin].copy()
                df_detail = df_detail.sort_values(
                    by='Tanggal', ascending=False)

                # Reorder columns
                cols = ['Tanggal', 'Lokasi_Kerja_Asli', 'Kode_Jabatan', 'Kode_Divisi', 'Kode_Area',
                        'Shift', 'Jam_Masuk', 'Jam_Keluar', 'Jam Lembur', 'Keterangan', 'Total_Scan']
                # Pastikan Kode_Area ada di dataframe (mencegah error jika CSV lama belum terupdate)
                if 'Kode_Area' not in df_detail.columns:
                    df_detail['Kode_Area'] = '-'
                if 'Lokasi_Kerja_Asli' not in df_detail.columns:
                    df_detail['Lokasi_Kerja_Asli'] = '-'
                if 'Kode_Jabatan' not in df_detail.columns:
                    df_detail['Kode_Jabatan'] = '-'
                if 'Kode_Divisi' not in df_detail.columns:
                    df_detail['Kode_Divisi'] = '-'
                df_detail = df_detail[cols]

                # Format tanggal dengan nama hari
                hari_indo = {
                    0: 'Senin', 1: 'Selasa', 2: 'Rabu', 3: 'Kamis',
                    4: 'Jumat', 5: 'Sabtu', 6: 'Minggu'
                }
                df_detail['Tanggal'] = pd.to_datetime(df_detail['Tanggal']).apply(
                    lambda x: f"{hari_indo[x.weekday()]}, {x.strftime('%Y-%m-%d')}"
                )

                # Statistik cepat
                total_hari = df_detail['Tanggal'].nunique()
                lembur_days = df_detail[df_detail['Jam Lembur']
                                        != '-'].shape[0]

                m1, m2 = st.columns(2)
                m1.metric("Total Kehadiran", f"{total_hari} Hari")
                m2.metric("Total Hari Lembur", f"{lembur_days} Hari")

                st.dataframe(df_detail, use_container_width=True,
                             hide_index=True)

                # --- BAGIAN KOMPARASI DATA ATASAN ---
                st.divider()
                st.header(
                    "⚖️ Komparasi dengan Data Atasan (t_absensi_solutions_harian.sql)")
                st.write(
                    "Berikut adalah data asli dari sistem atasan untuk karyawan yang sama dan pada rentang tanggal yang sama, sebagai bahan perbandingan.")

                df_boss = load_boss_data()
                if df_boss.empty:
                    st.warning(
                        "File t_absensi_solutions_harian.sql tidak ditemukan atau gagal dibaca.")
                else:
                    # Filter berdasarkan PIN dan rentang tanggal
                    df_boss_filtered = df_boss[df_boss['PIN'] == selected_pin]
                    mask_boss = (df_boss_filtered['Tanggal'] >= start_date.strftime(
                        '%Y-%m-%d')) & (df_boss_filtered['Tanggal'] <= end_date.strftime('%Y-%m-%d'))
                    df_boss_filtered = df_boss_filtered.loc[mask_boss]

                    # Format ulang kolom untuk kenyamanan baca
                    if not df_boss_filtered.empty:
                        # Urutkan berdasarkan tanggal terbaru di atas
                        df_boss_filtered = df_boss_filtered.sort_values(
                            by='Tanggal', ascending=False)
                        df_boss_filtered['Tanggal'] = pd.to_datetime(df_boss_filtered['Tanggal']).apply(
                            lambda x: f"{hari_indo[x.weekday()]}, {x.strftime('%Y-%m-%d')}"
                        )
                        st.dataframe(df_boss_filtered,
                                     use_container_width=True, hide_index=True)
                    else:
                        st.info(
                            "Tidak ada data untuk karyawan ini di file atasan pada rentang tanggal tersebut.")

                # --- BAGIAN RAW DATA ---
                st.divider()
                st.header("🔍 Riwayat Tap Mesin Mentah (Raw Logs)")
                st.write("Di bawah ini adalah data mentah setiap kali jari karyawan menempel di mesin absensi (tanpa ada proses pairing). Status IN/OUT berasal dari settingan default mesin.")

                df_raw = load_raw_data()
                if df_raw.empty:
                    st.warning("Data mentah tidak ditemukan.")
                else:
                    df_raw_filtered = df_raw[df_raw['PIN']
                                             == selected_pin].copy()
                    if not df_raw_filtered.empty:
                        mask_raw = (df_raw_filtered['Log_Time'].dt.date >= start_date) & (
                            df_raw_filtered['Log_Time'].dt.date <= end_date)
                        df_raw_filtered = df_raw_filtered.loc[mask_raw]

                        if not df_raw_filtered.empty:
                            # Urutkan berdasarkan waktu terbaru di atas
                            df_raw_filtered = df_raw_filtered.sort_values(
                                by='Log_Time', ascending=False)
                            df_raw_filtered['Tanggal'] = df_raw_filtered['Log_Time'].apply(
                                lambda x: f"{hari_indo[x.weekday()]}, {x.strftime('%Y-%m-%d')}"
                            )
                            df_raw_filtered['Jam'] = df_raw_filtered['Log_Time'].dt.strftime(
                                '%H:%M:%S')
                            df_raw_filtered['Nama_Karyawan'] = selected_name
                            cols_raw = [
                                'Kode_Area', 'PIN', 'Nama_Karyawan', 'Tanggal', 'Jam', 'Status']
                            st.dataframe(
                                df_raw_filtered[cols_raw], use_container_width=True, hide_index=True)
                        else:
                            st.info(
                                "Tidak ada log tap mesin mentah untuk karyawan ini pada rentang tanggal tersebut.")
                    else:
                        st.info("Karyawan ini tidak memiliki data log mentah.")

        # --- LAPORAN KORBAN SISTEM LAMA (GLOBAL, LEBAR PENUH) ---
        st.divider()
        st.header("🚨 Laporan Global: Korban Anomali Sistem Lama")
        st.write("Tabel di bawah ini menampilkan **seluruh daftar kejadian** di mana perhitungan sistem lama (atasan) dipastikan hancur karena memotong hari kalender di tengah shift malam atau karena lupa absen.")

        file_korban = "Laporan_Detail_Korban_Sistem_Lama.csv"
        if os.path.exists(file_korban):
            df_korban = pd.read_csv(file_korban)
            df_korban['PIN'] = df_korban['PIN'].astype(str)

            # Filter berdasarkan rentang tanggal dashboard
            if len(date_range) == 2:
                start_date, end_date = date_range
                mask_korban = (pd.to_datetime(df_korban['Tanggal']).dt.date >= start_date) & (
                    pd.to_datetime(df_korban['Tanggal']).dt.date <= end_date)
                df_korban_filtered = df_korban[mask_korban].copy()

                k1, k2, k3 = st.columns(3)
                k1.metric("Total Insiden (Di Rentang Ini)",
                          f"{len(df_korban_filtered)} Kejadian")
                k2.metric("Total Karyawan Terdampak",
                          f"{df_korban_filtered['PIN'].nunique()} Orang")

                jenis_kasus = st.multiselect(
                    "Filter Jenis Kasus:",
                    options=df_korban_filtered['Jenis_Kasus'].unique(),
                    default=df_korban_filtered['Jenis_Kasus'].unique()
                )

                if jenis_kasus:
                    df_korban_filtered = df_korban_filtered[df_korban_filtered['Jenis_Kasus'].isin(
                        jenis_kasus)]

                # Urutkan berdasarkan tanggal (terbaru di atas)
                df_korban_filtered = df_korban_filtered.sort_values(
                    by=['Tanggal', 'PIN'], ascending=[False, True])

                st.write(
                    "**💡 Klik pada baris mana saja untuk melihat bukti kerusakan datanya secara langsung!**")
                event_korban = st.dataframe(
                    df_korban_filtered,
                    use_container_width=True,
                    hide_index=True,
                    on_select="rerun",
                    selection_mode="single-row"
                )

                selected_korban_rows = event_korban.selection.rows
                if selected_korban_rows:
                    idx = selected_korban_rows[0]
                    korban_row = df_korban_filtered.iloc[idx]
                    k_pin = str(korban_row['PIN'])
                    k_nama = str(korban_row['Nama_Karyawan'])
                    k_tgl = str(korban_row['Tanggal'])
                    k_kasus = str(korban_row['Jenis_Kasus'])

                    st.subheader(f"🔎 Bukti Kerusakan Data: {k_nama}")
                    st.info(f"Kasus: **{k_kasus}** pada tanggal **{k_tgl}**")

                    c1, c2 = st.columns(2)
                    with c1:
                        st.markdown("**✅ Hasil Sistem Baru (Akurat)**")
                        # df adalah dataframe utama kita yang sudah di-load di atas
                        our_anomali = df[(df['PIN'].astype(str) == k_pin) & (
                            df['Tanggal'] == k_tgl)].copy()
                        if not our_anomali.empty:
                            st.dataframe(our_anomali[[
                                         'Tanggal', 'Shift', 'Jam_Masuk', 'Jam_Keluar', 'Keterangan']], hide_index=True, use_container_width=True)
                        else:
                            st.write("Data tidak ditemukan.")

                    with c2:
                        st.markdown(
                            "**❌ Hasil Sistem Atasan (Salah / Hancur)**")
                        df_boss_all = load_boss_data()
                        if not df_boss_all.empty:
                            boss_anomali = df_boss_all[(df_boss_all['PIN'].astype(
                                str) == k_pin) & (df_boss_all['Tanggal'] == k_tgl)].copy()
                            if not boss_anomali.empty:
                                st.dataframe(boss_anomali[[
                                             'Tanggal', 'Jam_Masuk_Atasan', 'Jam_Keluar_Atasan', 'Total_Jam_Kerja']], hide_index=True, use_container_width=True)
                            else:
                                st.error(
                                    "Data di sistem atasan kosong atau hilang untuk tanggal ini!")
                        else:
                            st.warning("Data atasan tidak dapat dimuat.")
        else:
            st.info(
                "File laporan korban belum tersedia. Silakan jalankan script `generate_victims.py`")


main()
