"""Primitif keamanan: hashing password (bcrypt), TOTP (pyotp), dan QR (SVG).

Modul ini menyendiri agar logika kriptografis terpisah dari route dan mudah
diuji. Semua perbandingan kredensial menggunakan fungsi constant-time bawaan
library (PRD Bab 7).
"""

import io
import re

import bcrypt
import pyotp
import qrcode
import qrcode.image.svg
from flask import current_app

# Username: huruf/angka/garis bawah/titik, 3–32 karakter.
USERNAME_RE = re.compile(r"^[A-Za-z0-9_.]{3,32}$")


# --- Password (bcrypt, FR-01) -------------------------------------------------

def hash_password(plain: str) -> str:
    """Mengembalikan hash bcrypt (string) dengan salt otomatis."""
    cost = current_app.config["BCRYPT_COST"]
    digest = bcrypt.hashpw(plain.encode("utf-8"), bcrypt.gensalt(rounds=cost))
    return digest.decode("utf-8")


def verify_password(plain: str, password_hash: str) -> bool:
    """Membandingkan password dengan hash secara constant-time."""
    try:
        return bcrypt.checkpw(plain.encode("utf-8"), password_hash.encode("utf-8"))
    except (ValueError, TypeError):
        return False


# --- TOTP (pyotp, FR-02 / FR-04) ---------------------------------------------

def generate_totp_secret() -> str:
    """Membuat secret base32 acak (32 karakter = 160 bit)."""
    return pyotp.random_base32()


def build_otpauth_uri(username: str, secret: str) -> str:
    """Membuat URI ``otpauth://`` untuk dipindai authenticator app."""
    issuer = current_app.config["OTP_ISSUER"]
    totp = pyotp.TOTP(
        secret,
        digits=current_app.config["OTP_DIGITS"],
        interval=current_app.config["OTP_INTERVAL"],
    )
    return totp.provisioning_uri(name=username, issuer_name=issuer)


def _totp(secret: str) -> pyotp.TOTP:
    return pyotp.TOTP(
        secret,
        digits=current_app.config["OTP_DIGITS"],
        interval=current_app.config["OTP_INTERVAL"],
    )


def verify_totp(secret: str, code: str) -> bool:
    """Memverifikasi kode 6 digit terhadap secret (toleransi 1 window drift)."""
    if not code or not code.isdigit():
        return False
    # valid_window=1 mengizinkan selisih jam ±1 interval (toleransi clock skew).
    return _totp(secret).verify(code, valid_window=1)


def matched_totp_counter(secret: str, code: str) -> int | None:
    """Mengembalikan nomor window (counter) yang cocok dengan kode, atau None.

    Diperlukan untuk proteksi replay (FR-09): server menyimpan counter terakhir
    yang sukses, dan menolak kode dari counter yang sama atau lebih lama.
    """
    import time

    if not code or not code.isdigit():
        return None
    totp = _totp(secret)
    interval = current_app.config["OTP_INTERVAL"]
    base = int(time.time()) // interval
    # Periksa window now-1, now, now+1 (selaras valid_window=1 di verify_totp).
    for counter in (base - 1, base, base + 1):
        if totp.verify(code, for_time=counter * interval, valid_window=0):
            return counter
    return None


# --- QR code (SVG, FR-02) -----------------------------------------------------

def qr_svg(data: str) -> str:
    """Menghasilkan QR code sebagai markup SVG (tanpa pillow)."""
    factory = qrcode.image.svg.SvgPathImage
    img = qrcode.make(data, image_factory=factory)
    buf = io.BytesIO()
    img.save(buf)
    return buf.getvalue().decode("utf-8")


# --- Validasi input (FR-06) ---------------------------------------------------

def validate_username(username: str) -> str | None:
    """Mengembalikan pesan error bila tidak valid, atau None bila valid."""
    if not username or not USERNAME_RE.match(username):
        return "Username harus 3–32 karakter (huruf, angka, titik, garis bawah)."
    return None


def validate_password(password: str) -> str | None:
    """Mengembalikan pesan error bila tidak valid, atau None bila valid."""
    min_len = current_app.config["PASSWORD_MIN_LENGTH"]
    if not password or len(password) < min_len:
        return f"Password minimal {min_len} karakter."
    return None
