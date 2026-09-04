import os
import sys
import subprocess

def main():
    # Pastikan current working directory ada di root project
    project_root = os.path.dirname(os.path.abspath(__file__))
    os.chdir(project_root)
    
    # Tambahkan 'app' ke sys.path supaya import di streamlit bisa jalan mulus
    sys.path.insert(0, os.path.join(project_root, 'app'))

    # Jalankan streamlit
    app_path = os.path.join('app', 'dashboard.py')
    
    print("Mulai menjalankan Lisa Absensi Dashboard...")
    try:
        subprocess.run([sys.executable, "-m", "streamlit", "run", app_path], check=True)
    except KeyboardInterrupt:
        print("\nSistem dimatikan dengan aman.")
    except Exception as e:
        print(f"Gagal menjalankan dashboard: {e}")

if __name__ == "__main__":
    main()
