"""Suite pengujian keamanan — memetakan PRD Bab 9 (TS-01..TS-10) & kebutuhan FR.

Jalankan:  pytest -v

Setiap test mencantumkan kode skenario (TS-xx) atau kebutuhan (FR-xx) yang
dibuktikannya, sehingga dapat dijadikan lampiran bukti uji pada laporan.
"""

import sqlite3
import time

import pyotp
import pytest

from conftest import register, login_password, login_otp, PASSWORD


def db_conn(app):
    return sqlite3.connect(app.config["DATABASE"])


# ===== Registrasi & penyimpanan password ====================================

def test_fr01_password_disimpan_sebagai_hash_bcrypt(app, client):
    """FR-01 / TS-02: password tersimpan sebagai hash bcrypt, bukan plaintext."""
    register(client, "budi")
    row = db_conn(app).execute(
        "SELECT password_hash FROM users WHERE username='budi'"
    ).fetchone()
    assert row[0].startswith("$2b$")
    assert PASSWORD not in row[0]


def test_ts03_password_sama_hash_berbeda(app, client):
    """TS-03: dua akun dengan password sama menghasilkan hash berbeda (salt unik)."""
    register(client, "budi")
    register(client, "ani")
    rows = db_conn(app).execute(
        "SELECT password_hash FROM users WHERE username IN ('budi','ani')"
    ).fetchall()
    assert rows[0][0] != rows[1][0]


def test_fr02_qr_dan_secret_ditampilkan(client):
    """FR-02: registrasi menampilkan QR (SVG) dan secret base32."""
    secret = register(client, "budi")
    assert len(secret) >= 32  # 160-bit base32


def test_fr06_password_pendek_ditolak(client):
    """FR-06: password < 8 karakter ditolak."""
    r = client.post("/register", data={"username": "cici", "password": "short"})
    assert "minimal" in r.get_data(as_text=True).lower()


def test_fr06_username_duplikat_ditolak(client):
    """FR-06: username unik — duplikat ditolak."""
    register(client, "budi")
    r = client.post("/register", data={"username": "budi", "password": PASSWORD})
    assert "sudah terpakai" in r.get_data(as_text=True)


# ===== Login tahap 1 (password) =============================================

def test_ts01_password_salah_ditolak(client):
    """TS-01: password salah → ditolak dengan pesan generik, tidak lanjut ke OTP."""
    register(client, "budi")
    r = client.post("/login", data={"username": "budi", "password": "salahsalah"})
    body = r.get_data(as_text=True)
    assert r.status_code == 200 and "salah" in body.lower()
    # tidak ada sesi pending → akses tahap OTP dialihkan
    assert client.get("/login/otp").status_code == 302


def test_ts01_pesan_generik_user_tidak_ada(client):
    """TS-01 / NFR: username tidak ada memberi pesan yang sama dengan password salah."""
    r = client.post("/login", data={"username": "hantu", "password": "apapun123"})
    assert "Username atau password salah" in r.get_data(as_text=True)


# ===== Login tahap 2 (OTP) & proteksi sesi ==================================

def test_alur_sukses_lengkap(client):
    """Alur happy-path: registrasi → password → OTP benar → dashboard."""
    secret = register(client, "budi")
    login_password(client, "budi")
    r = login_otp(client, secret, follow_redirects=True)
    body = r.get_data(as_text=True)
    assert "Dashboard" in body and "budi" in body


def test_ts04_otp_salah_ditolak(client):
    """TS-04: OTP salah → ditolak, sesi tidak terbentuk."""
    register(client, "budi")
    login_password(client, "budi")
    r = client.post("/login/otp", data={"otp": "000000"})
    assert "salah" in r.get_data(as_text=True).lower()
    assert client.get("/dashboard").status_code == 302


def test_ts05_otp_kadaluwarsa_ditolak(client):
    """TS-05: kode OTP dari window lampau (> toleransi) ditolak."""
    secret = register(client, "budi")
    login_password(client, "budi")
    # kode dari ~90 detik lalu (≥ 3 window) berada di luar toleransi ±1 window
    old_code = pyotp.TOTP(secret).at(int(time.time()) - 90)
    r = client.post("/login/otp", data={"otp": old_code})
    assert "salah" in r.get_data(as_text=True).lower() or "kadaluwarsa" in r.get_data(as_text=True).lower()
    assert client.get("/dashboard").status_code == 302


def test_ts06_dashboard_tanpa_login_dialihkan(client):
    """TS-06: akses dashboard tanpa login → dialihkan ke login."""
    r = client.get("/dashboard")
    assert r.status_code == 302 and "/login" in r.headers["Location"]


def test_ts07_bypass_otp_ditolak(client):
    """TS-07: akses dashboard setelah hanya tahap-1 (password) → ditolak."""
    register(client, "budi")
    login_password(client, "budi")  # tahap 1 sukses, OTP belum
    r = client.get("/dashboard")
    assert r.status_code == 302 and "/login" in r.headers["Location"]


def test_ts08_sql_injection_login(app, client):
    """TS-08: input SQLi diperlakukan sebagai data biasa; tidak ada error DB."""
    register(client, "budi")
    r = client.post("/login", data={"username": "' OR 1=1 --", "password": "x"})
    assert r.status_code == 200
    assert "salah" in r.get_data(as_text=True).lower()
    # database tetap utuh
    cnt = db_conn(app).execute("SELECT COUNT(*) FROM users").fetchone()[0]
    assert cnt == 1


def test_fr07_logout_mengakhiri_sesi(client):
    """FR-07: setelah logout, dashboard ditolak."""
    secret = register(client, "budi")
    login_password(client, "budi")
    login_otp(client, secret)
    assert client.get("/dashboard").status_code == 200
    client.post("/logout")
    assert client.get("/dashboard").status_code == 302


# ===== Fitur P1 =============================================================

def test_ts10_replay_otp_ditolak(client):
    """TS-10 / FR-09: kode OTP yang sudah berhasil dipakai tidak bisa dipakai ulang."""
    secret = register(client, "budi")
    code = pyotp.TOTP(secret).now()
    # login pertama dengan kode tsb. → sukses
    login_password(client, "budi")
    r1 = client.post("/login/otp", data={"otp": code}, follow_redirects=True)
    assert "Dashboard" in r1.get_data(as_text=True)
    client.post("/logout")
    # login kedua memakai ULANG kode yang sama → ditolak (replay)
    login_password(client, "budi")
    r2 = client.post("/login/otp", data={"otp": code})
    assert "Dashboard" not in r2.get_data(as_text=True)
    assert client.get("/dashboard").status_code == 302


def test_ts09_rate_limiting(client):
    """TS-09 / FR-08: 5 kegagalan beruntun → percobaan berikutnya ditunda."""
    register(client, "rina")
    for _ in range(5):
        client.post("/login", data={"username": "rina", "password": "salahsalah"})
    # percobaan ke-6 dengan password BENAR pun ditunda
    r = client.post("/login", data={"username": "rina", "password": PASSWORD})
    assert "Terlalu banyak" in r.get_data(as_text=True)


def test_fr10_audit_log_tanpa_kredensial(app, client):
    """FR-10: percobaan login tercatat; tabel tidak menyimpan password/OTP."""
    register(client, "rina")
    client.post("/login", data={"username": "rina", "password": "salahsalah"})
    con = db_conn(app)
    cnt = con.execute(
        "SELECT COUNT(*) FROM login_attempts WHERE username='rina'"
    ).fetchone()[0]
    assert cnt >= 1
    cols = [r[1] for r in con.execute("PRAGMA table_info(login_attempts)")]
    assert "password" not in cols and "otp" not in cols and "code" not in cols
