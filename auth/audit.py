"""Audit log percobaan autentikasi (FR-10) dan rate limiting (FR-08).

Tabel ``login_attempts`` mencatat setiap percobaan login (berhasil/gagal) dengan
timestamp, username, tahap, dan alamat IP — TANPA pernah menyimpan password
maupun kode OTP.
"""

from flask import current_app, request

from db import get_db


def _client_ip() -> str:
    """Alamat IP klien (mempertimbangkan proxy sederhana)."""
    fwd = request.headers.get("X-Forwarded-For", "")
    if fwd:
        return fwd.split(",")[0].strip()
    return request.remote_addr or "unknown"


def log_attempt(username: str, status: str, stage: str) -> None:
    """Mencatat satu percobaan login.

    status: 'sukses' | 'gagal'    stage: 'password' | 'otp'
    """
    db = get_db()
    db.execute(
        "INSERT INTO login_attempts (username, status, stage, ip_address) "
        "VALUES (?, ?, ?, ?)",
        (username, status, stage, _client_ip()),
    )
    db.commit()


def recent_failures(username: str) -> int:
    """Jumlah kegagalan beruntun untuk username dalam jendela waktu.

    "Beruntun" dihitung sebagai kegagalan setelah login sukses terakhir,
    dibatasi jendela ``RATE_LIMIT_WINDOW_MIN`` menit terakhir.
    """
    db = get_db()
    window = current_app.config["RATE_LIMIT_WINDOW_MIN"]

    # Hanya login PENUH (sukses di tahap OTP) yang me-reset hitungan kegagalan,
    # agar brute-force OTP tidak bisa di-reset hanya dengan mengulang password.
    last_success = db.execute(
        "SELECT MAX(id) FROM login_attempts "
        "WHERE username = ? AND status = 'sukses' AND stage = 'otp'",
        (username,),
    ).fetchone()[0] or 0

    row = db.execute(
        "SELECT COUNT(*) FROM login_attempts "
        "WHERE username = ? AND status = 'gagal' AND id > ? "
        f"AND created_at > datetime('now', '-{int(window)} minutes')",
        (username, last_success),
    ).fetchone()
    return row[0]


def is_rate_limited(username: str) -> bool:
    """True bila username melampaui batas kegagalan (FR-08)."""
    if not username:
        return False
    return recent_failures(username) >= current_app.config["RATE_LIMIT_MAX"]
