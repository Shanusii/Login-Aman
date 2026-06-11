"""Fixture pytest untuk Sistem Login Aman.

Setiap test mendapat aplikasi dengan database SQLite sementara yang bersih,
sehingga test saling terisolasi dan dapat dijalankan ulang.
"""

import re
import sys
from pathlib import Path

import pyotp
import pytest

# Pastikan root proyek ada di sys.path agar `import app` berfungsi.
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app import create_app  # noqa: E402
from config import Config  # noqa: E402
import db as db_module  # noqa: E402


@pytest.fixture
def app(tmp_path):
    class TestConfig(Config):
        TESTING = True
        SECRET_KEY = "test-secret"
        DATABASE = tmp_path / "test.db"
        SESSION_TYPE = "filesystem"
        SESSION_FILE_DIR = str(tmp_path / "sessions")

    application = create_app(TestConfig)
    with application.app_context():
        db_module.init_db()
    return application


@pytest.fixture
def client(app):
    return app.test_client()


# --- Helper yang dipakai banyak test --------------------------------------

PASSWORD = "Password123!"


def register(client, username, password=PASSWORD):
    """Mendaftarkan akun; mengembalikan secret TOTP-nya."""
    html = client.post(
        "/register", data={"username": username, "password": password}
    ).get_data(as_text=True)
    match = re.search(r'class="secret">([A-Z2-7]+)<', html)
    assert match, "secret TOTP tidak ditemukan di halaman sukses registrasi"
    return match.group(1)


def login_password(client, username, password=PASSWORD):
    return client.post(
        "/login", data={"username": username, "password": password}
    )


def login_otp(client, secret, follow_redirects=False):
    code = pyotp.TOTP(secret).now()
    return client.post(
        "/login/otp", data={"otp": code}, follow_redirects=follow_redirects
    )


@pytest.fixture
def helpers():
    """Akses helper sebagai satu objek di dalam test."""
    class _H:
        register = staticmethod(register)
        login_password = staticmethod(login_password)
        login_otp = staticmethod(login_otp)
        PASSWORD = PASSWORD

    return _H
