"""Titik masuk aplikasi Sistem Login Aman (Flask application factory).

Jalankan:
    flask --app app init-db      # sekali, untuk membuat database
    flask --app app run --debug  # menjalankan server pengembangan
"""

from flask import Flask, redirect, url_for
from flask_session import Session

import db
from config import Config


def create_app(config_class: type = Config) -> Flask:
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Pastikan folder DB ada (untuk database & sesi) — mengikuti config aktif.
    from pathlib import Path
    Path(app.config["DATABASE"]).parent.mkdir(parents=True, exist_ok=True)

    # Inisialisasi ekstensi.
    Session(app)
    db.init_app(app)

    # Registrasi blueprint autentikasi (Fase 2 mengisi logikanya).
    from auth import bp as auth_bp
    app.register_blueprint(auth_bp)

    @app.route("/")
    def index():
        # Arahkan langsung ke halaman login sebagai titik masuk utama.
        return redirect(url_for("auth.login"))

    return app


# Objek aplikasi untuk `flask --app app run`.
app = create_app()


if __name__ == "__main__":
    app.run(debug=True)
