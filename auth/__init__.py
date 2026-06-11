"""Blueprint autentikasi — alur registrasi & login dua tahap (Fase 2).

Mengimplementasikan FR-01..FR-05 dan FR-07:
  - Registrasi dengan hashing bcrypt + pembuatan secret TOTP & QR (FR-01, FR-02)
  - Login tahap 1: verifikasi password (FR-03)
  - Login tahap 2: verifikasi TOTP, baru membuat sesi penuh (FR-04)
  - Proteksi dashboard via dekorator ``login_required`` (FR-05)
  - Logout (FR-07)

Catatan keamanan: pesan kegagalan login bersifat generik (tidak membedakan
"username tidak ada" vs "password salah") sesuai PRD Bab 7 & US-04.
"""

import sqlite3
from functools import wraps

from flask import (
    Blueprint,
    render_template,
    request,
    redirect,
    url_for,
    flash,
    session,
)

from db import get_db
from . import security
from . import audit

bp = Blueprint("auth", __name__)

# Pesan generik tunggal untuk semua kegagalan login (anti user-enumeration).
GENERIC_LOGIN_ERROR = "Username atau password salah."
RATE_LIMIT_MESSAGE = (
    "Terlalu banyak percobaan gagal. Silakan coba lagi dalam beberapa menit."
)


def login_required(view):
    """Dekorator: tolak akses bila sesi penuh belum terbentuk (FR-05)."""
    @wraps(view)
    def wrapped(*args, **kwargs):
        if session.get("user_id") is None:
            flash("Silakan masuk terlebih dahulu.", "error")
            return redirect(url_for("auth.login"))
        return view(*args, **kwargs)
    return wrapped


# --- Registrasi (FR-01, FR-02) -----------------------------------------------

@bp.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = (request.form.get("username") or "").strip()
        password = request.form.get("password") or ""

        # Validasi input (FR-06).
        error = security.validate_username(username) or security.validate_password(password)
        if error:
            flash(error, "error")
            return render_template("register.html", username=username)

        # Hash password (FR-01) + buat secret TOTP (FR-02).
        password_hash = security.hash_password(password)
        totp_secret = security.generate_totp_secret()

        db = get_db()
        try:
            db.execute(
                "INSERT INTO users (username, password_hash, totp_secret) VALUES (?, ?, ?)",
                (username, password_hash, totp_secret),
            )
            db.commit()
        except sqlite3.IntegrityError:
            flash("Username sudah terpakai. Silakan pilih yang lain.", "error")
            return render_template("register.html", username=username)

        # Tampilkan QR sekali agar pengguna memindainya (US-02).
        otpauth_uri = security.build_otpauth_uri(username, totp_secret)
        qr = security.qr_svg(otpauth_uri)
        return render_template(
            "register_success.html",
            username=username,
            qr_svg=qr,
            secret=totp_secret,
        )

    return render_template("register.html")


# --- Login tahap 1: password (FR-03) -----------------------------------------

@bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = (request.form.get("username") or "").strip()
        password = request.form.get("password") or ""

        # Rate limiting (FR-08): tolak lebih awal bila terlalu banyak kegagalan.
        if audit.is_rate_limited(username):
            flash(RATE_LIMIT_MESSAGE, "error")
            return render_template("login.html", username=username)

        db = get_db()
        user = db.execute(
            "SELECT id, username, password_hash FROM users WHERE username = ?",
            (username,),
        ).fetchone()

        # Verifikasi bcrypt. Pesan selalu generik bila gagal.
        if user is None or not security.verify_password(password, user["password_hash"]):
            audit.log_attempt(username, "gagal", "password")
            flash(GENERIC_LOGIN_ERROR, "error")
            return render_template("login.html", username=username)

        # Sukses tahap 1: simpan status "menunggu OTP" — BUKAN sesi penuh (FR-03).
        audit.log_attempt(username, "sukses", "password")
        session.clear()
        session["pending_user_id"] = user["id"]
        session["pending_username"] = user["username"]
        return redirect(url_for("auth.login_otp"))

    return render_template("login.html")


# --- Login tahap 2: TOTP (FR-04) ---------------------------------------------

@bp.route("/login/otp", methods=["GET", "POST"])
def login_otp():
    pending_id = session.get("pending_user_id")
    # Tidak boleh ke tahap 2 tanpa lulus tahap 1 (cegah bypass — TS-07).
    if pending_id is None:
        flash("Sesi verifikasi tidak ditemukan. Silakan masuk ulang.", "error")
        return redirect(url_for("auth.login"))

    pending_username = session.get("pending_username")

    if request.method == "POST":
        code = (request.form.get("otp") or "").strip()

        # Rate limiting juga berlaku di tahap OTP (FR-08).
        if audit.is_rate_limited(pending_username):
            flash(RATE_LIMIT_MESSAGE, "error")
            return render_template("login_otp.html")

        db = get_db()
        user = db.execute(
            "SELECT id, username, totp_secret, last_totp_counter FROM users WHERE id = ?",
            (pending_id,),
        ).fetchone()

        counter = None
        if user is not None:
            counter = security.matched_totp_counter(user["totp_secret"], code)

        # Kode salah/kadaluwarsa (FR-04) ATAU sudah dipakai (replay, FR-09).
        if user is None or counter is None or counter <= user["last_totp_counter"]:
            audit.log_attempt(pending_username, "gagal", "otp")
            flash("Kode OTP salah, kadaluwarsa, atau sudah digunakan.", "error")
            return render_template("login_otp.html")

        # Catat counter yang dipakai agar tidak bisa di-replay (FR-09).
        db.execute(
            "UPDATE users SET last_totp_counter = ? WHERE id = ?",
            (counter, user["id"]),
        )
        db.commit()
        audit.log_attempt(pending_username, "sukses", "otp")

        # Sukses tahap 2: bentuk sesi penuh.
        session.clear()
        session["user_id"] = user["id"]
        session["username"] = user["username"]
        flash("Login berhasil. Selamat datang!", "success")
        return redirect(url_for("auth.dashboard"))

    return render_template("login_otp.html")


# --- Dashboard terproteksi (FR-05) -------------------------------------------

@bp.route("/dashboard")
@login_required
def dashboard():
    return render_template("dashboard.html", username=session.get("username"))


# --- Logout (FR-07) -----------------------------------------------------------

@bp.route("/logout", methods=["POST"])
def logout():
    session.clear()
    flash("Anda telah keluar.", "info")
    return redirect(url_for("auth.login"))
