import socket
import subprocess
import platform
import traceback
from zk import ZK

def print_step(step_num, message):
    print(f"\n[STEP {step_num}] {message}")

def check_ping(ip):
    print_step(1, f"Mengecek apakah IP {ip} bisa di-Ping (apakah komputer ini satu jaringan dengan mesin absensi?)...")
    
    # Menentukan argumen ping berdasarkan OS (Windows menggunakan -n, Linux/Mac menggunakan -c)
    param = '-n' if platform.system().lower() == 'windows' else '-c'
    command = ['ping', param, '1', ip]
    
    try:
        output = subprocess.check_output(command, stderr=subprocess.STDOUT, universal_newlines=True)
        if "TTL=" in output or "ttl=" in output:
            print("  [+] SUKSES: Mesin merespon Ping. (Jaringan terhubung)")
            return True
        else:
            print("  [-] GAGAL: Tidak ada balasan Ping.")
            print(f"      Detail log:\n      {output.strip()}")
            return False
    except subprocess.CalledProcessError as e:
        print("  [-] GAGAL: Perintah Ping gagal dieksekusi atau tidak ada balasan.")
        print(f"      Detail log:\n      {e.output.strip()}")
        return False

def check_tcp_port(ip, port):
    print_step(2, f"Mengecek apakah Jalur TCP (Port {port}) terbuka di IP {ip}...")
    
    # Membuat socket TCP murni tanpa library ZK
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(5) # Set timeout 5 detik
    
    try:
        result = sock.connect_ex((ip, port))
        if result == 0:
            print(f"  [+] SUKSES: Port {port} TERBUKA dan bisa diakses.")
            sock.close()
            return True
        else:
            print(f"  [-] GAGAL: Port {port} TERTUTUP atau terhalang Firewall. (Kode Error: {result})")
            sock.close()
            return False
    except socket.error as e:
        print(f"  [-] GAGAL: Terjadi error pada level socket jaringan. Error: {e}")
        sock.close()
        return False

def test_zk_library(ip, port, password):
    print_step(3, "Mencoba komunikasi data mesin absensi menggunakan library pyzk...")
    
    zk = ZK(ip, port=port, timeout=5, password=password, force_udp=False, ommit_ping=True)
    conn = None
    try:
        print("  [*] Sedang menginisiasi koneksi ZK...")
        conn = zk.connect()
        print("  [+] SUKSES: Koneksi pyzk berhasil!")
        
        # Test baca 1 data kecil
        sn = conn.get_serialnumber()
        print(f"  [+] Berhasil membaca Serial Number mesin: {sn}")
        
    except socket.timeout:
        print("  [-] GAGAL (Timeout): Koneksi terlalu lama tidak direspon oleh mesin. (Jaringan lambat atau diblokir)")
    except Exception as e:
        print(f"  [-] GAGAL (Exception ZK): {e}")
        print("      Detail Stacktrace (mirip Go error stack):")
        traceback.print_exc(limit=2)
    finally:
        if conn:
            conn.disconnect()
            print("  [*] Koneksi pyzk ditutup.")

def main():
    print("==========================================================")
    print("      DIAGNOSTIK KONEKSI MESIN ABSENSI MENDALAM           ")
    print("==========================================================")
    
    devices = [
        {"name": "SF 1", "ip": "192.168.16.2", "port": 4370, "password": 1234},
        # Kita tes satu mesin dulu agar outputnya tidak terlalu panjang
    ]

    for dev in devices:
        print(f"\n>>> MEMULAI DEBUG UNTUK MESIN: {dev['name']} ({dev['ip']}:{dev['port']}) <<<")
        
        ping_ok = check_ping(dev['ip'])
        port_ok = check_tcp_port(dev['ip'], dev['port'])
        
        if not ping_ok and not port_ok:
            print("\n[KESIMPULAN DIAGNOSTIK SEMENTARA]")
            print("Penyebab Gagal: Komputer Anda sama sekali tidak memiliki jalur jaringan menuju 192.168.16.2.")
            print("Saran: Pastikan Anda sudah terhubung ke VPN kantor cabang, atau berada di satu jaringan WiFi yang sama dengan mesin absensi.")
            print("Langkah 3 (pyzk) tetap akan kita coba, tapi 99% akan gagal.\n")
        elif ping_ok and not port_ok:
            print("\n[KESIMPULAN DIAGNOSTIK SEMENTARA]")
            print("Penyebab Gagal: Komputer Anda BISA terhubung ke jaringan mesin, TAPI jalurnya (Port 4370) DIBLOKIR.")
            print("Saran: Cek apakah ada Firewall di router kantor atau di mesin absensi yang memblokir port tersebut.")
            
        test_zk_library(dev['ip'], dev['port'], dev['password'])
        
        print("\n----------------------------------------------------------\n")

if __name__ == "__main__":
    main()
