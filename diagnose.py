import sqlite3
import time
import urllib.request
import email.utils
import datetime
from pathlib import Path

# Coba import pyotp. Jika tidak ada, beri tahu user untuk install.
try:
    import pyotp
except ImportError:
    print("Error: Library 'pyotp' belum terinstall.")
    print("Silakan jalankan: pip install pyotp")
    exit(1)

DB_PATH = Path(__file__).parent / "instance" / "app.db"

def get_google_time():
    try:
        req = urllib.request.Request('https://www.google.com', method='HEAD')
        with urllib.request.urlopen(req, timeout=5) as response:
            date_str = response.headers.get('Date')
            if date_str:
                return email.utils.parsedate_to_datetime(date_str)
    except Exception as e:
        print(f"Gagal mengambil waktu dari Google: {e}")
    return None

def main():
    print("=== DIAGNOSIS SISTEM TOTP / OTP ===")
    
    # 1. Cek Waktu Sistem
    local_now = datetime.datetime.now()
    utc_now = datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)
    
    print(f"Waktu Lokal PC Saat Ini : {local_now.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Waktu UTC PC Saat Ini   : {utc_now.strftime('%Y-%m-%d %H:%M:%S')}")
    
    print("Menghubungi Google untuk mengecek waktu internet asli...")
    real_utc = get_google_time()
    
    if real_utc:
        # datetime.datetime.utcnow() naive, real_utc aware. Ubah real_utc jadi naive UTC.
        real_utc_naive = real_utc.replace(tzinfo=None)
        diff_seconds = (utc_now - real_utc_naive).total_seconds()
        print(f"Waktu Internet Asli    : {real_utc_naive.strftime('%Y-%m-%d %H:%M:%S')} UTC")
        print(f"Selisih Waktu PC Anda  : {diff_seconds:+.2f} detik")
        if abs(diff_seconds) > 15:
            print("\n[PERINGATAN] Jam PC Anda tidak akurat!")
            print("Selisih waktu lebih dari 15 detik dapat menyebabkan verifikasi OTP gagal.")
            print("Silakan sinkronkan jam PC Anda ke waktu internet otomatis (Sync Now).\n")
        else:
            print("-> Jam PC Anda sudah akurat (sinkron dengan internet).\n")
    else:
        print("-> Tidak dapat memverifikasi selisih waktu karena koneksi gagal.\n")

    # 2. Baca Database
    if not DB_PATH.exists():
        print(f"Database tidak ditemukan di {DB_PATH}.")
        print("Silakan inisialisasi database terlebih dahulu (flask init-db).")
        return

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    try:
        users = cursor.execute("SELECT id, username, totp_secret, last_totp_counter FROM users").fetchall()
    except sqlite3.OperationalError as e:
        print(f"Gagal membaca tabel users: {e}")
        conn.close()
        return

    if not users:
        print("Tidak ada user terdaftar di database.")
        conn.close()
        return

    print("--- Kode OTP yang Diharapkan saat ini ---")
    for user in users:
        username = user["username"]
        secret = user["totp_secret"]
        last_counter = user["last_totp_counter"]
        
        totp = pyotp.TOTP(secret, interval=30)
        current_otp = totp.now()
        
        # Cari tahu counter saat ini
        current_counter = int(time.time()) // 30
        
        print(f"\nUser: {username}")
        print(f"  Secret Key (Base32)  : {secret}")
        print(f"  Counter Terakhir     : {last_counter}")
        print(f"  Counter Saat Ini     : {current_counter}")
        print(f"  Kode OTP Sekarang    : {current_otp}")
        
        # Tampilkan juga OTP sebelumnya dan setelahnya untuk toleransi window
        prev_otp = pyotp.TOTP(secret, interval=30).at(time.time() - 30)
        next_otp = pyotp.TOTP(secret, interval=30).at(time.time() + 30)
        print(f"  Kode OTP (-30 detik) : {prev_otp}")
        print(f"  Kode OTP (+30 detik) : {next_otp}")
        
        if current_counter <= last_counter:
            print("  [PERINGATAN] Counter saat ini sudah pernah digunakan atau di bawah counter terakhir (Anti-Replay aktif).")
            print("  Anda harus menunggu 30-60 detik untuk mencoba OTP yang baru.")
            
    conn.close()

if __name__ == "__main__":
    main()
