"""Lapisan akses database SQLite.

Menyediakan koneksi per-request (disimpan di ``flask.g``) dan inisialisasi
skema dari ``schema.sql``. Seluruh query di aplikasi WAJIB menggunakan
parameterized query (placeholder ``?``) untuk mencegah SQL injection (FR-06).
"""

import sqlite3
from pathlib import Path

import click
from flask import current_app, g


def get_db() -> sqlite3.Connection:
    """Mengembalikan koneksi database untuk request saat ini.

    Koneksi dibuat sekali per request dan dipakai ulang via ``g``.
    """
    if "db" not in g:
        db_path = current_app.config["DATABASE"]
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        g.db = sqlite3.connect(
            db_path,
            detect_types=sqlite3.PARSE_DECLTYPES,
        )
        # Akses kolom berdasarkan nama (row["username"]).
        g.db.row_factory = sqlite3.Row
        # Aktifkan penegakan foreign key.
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db


def close_db(exception=None) -> None:
    """Menutup koneksi database di akhir request."""
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db() -> None:
    """Membuat tabel dari schema.sql (idempoten) lalu menjalankan migrasi ringan."""
    db = get_db()
    schema_path = Path(current_app.root_path) / "schema.sql"
    with open(schema_path, "r", encoding="utf-8") as f:
        db.executescript(f.read())
    _migrate(db)
    db.commit()


def _migrate(db: sqlite3.Connection) -> None:
    """Menambahkan kolom baru pada DB lama tanpa kehilangan data (idempoten)."""
    cols = {row["name"] for row in db.execute("PRAGMA table_info(users)")}
    if "last_totp_counter" not in cols:
        db.execute(
            "ALTER TABLE users ADD COLUMN last_totp_counter INTEGER NOT NULL DEFAULT 0"
        )


@click.command("init-db")
def init_db_command() -> None:
    """Perintah CLI: ``flask init-db`` untuk menginisialisasi database."""
    init_db()
    click.echo("Database berhasil diinisialisasi.")


def init_app(app) -> None:
    """Mendaftarkan teardown dan perintah CLI ke aplikasi Flask."""
    app.teardown_appcontext(close_db)
    app.cli.add_command(init_db_command)
