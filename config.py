"""Konfigurasi aplikasi Sistem Login Aman.

Nilai sensitif (SECRET_KEY) sebaiknya diambil dari environment variable di
lingkungan nyata. Untuk demonstrasi akademik lokal, disediakan default yang
jelas-jelas hanya untuk pengembangan.
"""

import os
from pathlib import Path

# Direktori basis proyek (folder tempat file ini berada).
BASE_DIR = Path(__file__).resolve().parent


class Config:
    # Kunci untuk menandatangani session cookie. WAJIB diganti via env di produksi.
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-only-secret-change-me")

    # Lokasi file database SQLite.
    DATABASE = BASE_DIR / "instance" / "app.db"

    # --- Parameter keamanan (sesuai PRD Bab 7) ---
    BCRYPT_COST = 12          # cost factor bcrypt (>= 12)
    OTP_DIGITS = 6            # panjang kode TOTP
    OTP_INTERVAL = 30         # window TOTP dalam detik (RFC 6238)
    OTP_ISSUER = "LoginAman"  # nama issuer yang tampil di authenticator app
    PASSWORD_MIN_LENGTH = 8   # panjang minimum password

    # --- Rate limiting (FR-08) ---
    RATE_LIMIT_MAX = 5         # maksimum kegagalan beruntun
    RATE_LIMIT_WINDOW_MIN = 15  # jendela waktu (menit) untuk menghitung kegagalan

    # --- Manajemen sesi ---
    SESSION_TYPE = "filesystem"
    SESSION_FILE_DIR = str(BASE_DIR / "instance" / "sessions")
    SESSION_PERMANENT = False
    SESSION_COOKIE_HTTPONLY = True   # cegah akses cookie via JavaScript (XSS)
    SESSION_COOKIE_SAMESITE = "Lax"  # mitigasi CSRF dasar
