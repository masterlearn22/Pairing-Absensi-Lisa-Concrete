import datetime

from zk import ZK, const

def connect_and_get_logs(name, ip, port, password):
    print(f"\n--- Mengambil log dari {name} ({ip}:{port}) ---")
    zk = ZK(ip, port=port, timeout=5, password=password, force_udp=False, ommit_ping=True)
    
    conn = None
    try:
        # Melakukan koneksi ke mesin
        print(f"Menghubungkan ke {name}...")
        conn = zk.connect()
        print("Koneksi berhasil!")
        
        # Disable mesin sementara agar tidak ada yang absen saat kita tarik data (opsional tapi disarankan)
        conn.disable_device()
        
        # Mendapatkan info user
        users = conn.get_users()
        print(f"Total User di mesin: {len(users)}")
        
        # Mendapatkan log absensi
        print("Mengambil data absensi...")
        attendance = conn.get_attendance()
        print(f"Total Log Absensi yang ditemukan: {len(attendance)}")
        
        # Menampilkan 5 log terakhir sebagai contoh
        if attendance:
            print("\n5 Log Terakhir:")
            for att in attendance[-5:]:
                print(f"User ID: {att.user_id}, Waktu: {att.timestamp}, Status: {att.status}")
                
        # Jika Anda ingin menyimpan ke database (MySQL/PostgreSQL), kodenya bisa ditaruh di sini
        # Contoh: insert_to_db(attendance)
        
    except Exception as e:
        print(f"Gagal menghubungkan ke {name}: {e}")
    finally:
        if conn:
            # Enable mesin kembali
            conn.enable_device()
            # Putus koneksi
            conn.disconnect()
            print("Koneksi ditutup.")

def main():
    # Daftar perangkat berdasarkan catatan yang Anda berikan
    devices = [
        {"name": "SF 1", "ip": "192.168.16.2", "port": 4370, "password": 1234},
        {"name": "SF 2", "ip": "192.168.16.2", "port": 4372, "password": 1234},
        {"name": "SF 3", "ip": "192.168.16.2", "port": 4373, "password": 1234},
    ]

    for device in devices:
        connect_and_get_logs(
            name=device["name"],
            ip=device["ip"],
            port=device["port"],
            password=device["password"]
        )

if __name__ == "__main__":
    main()
