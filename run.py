import os
import sys

def main():
    # Pastikan current working directory ada di root project
    project_root = os.path.dirname(os.path.abspath(__file__))
    os.chdir(project_root)
    
    # Tambahkan 'app' ke sys.path supaya import di streamlit bisa jalan mulus
    sys.path.insert(0, os.path.join(project_root, 'app'))

    app_path = os.path.join('app', 'dashboard.py')
    print("Mulai menjalankan Lisa Absensi Dashboard...")
    
    # Menjalankan streamlit langsung di dalam proses (tanpa subprocess)
    # Ini mencegah masalah looping/tab browser terbuka berkali-kali.
    try:
        from streamlit.web import cli as stcli
    except ImportError:
        import streamlit.cli as stcli
        
    sys.argv = ["streamlit", "run", app_path]
    sys.exit(stcli.main())

if __name__ == "__main__":
    main()
