# Sistem Login Aman — OTP & Hashing Password

Proyek mata kuliah **Keamanan Informasi**: sistem login dengan autentikasi dua
faktor (2FA) menggabungkan **bcrypt** (hashing password) dan **TOTP** (One-Time
Password berbasis waktu, RFC 6238) yang kompatibel dengan Google Authenticator.

Spesifikasi lengkap ada di [PRD.md](PRD.md).

## Stack

| Komponen | Teknologi |
|---|---|
| Framework web | Flask |
| Hashing password | bcrypt (cost ≥ 12) |
| OTP (TOTP) | pyotp |
| QR code | qrcode (SVG, tanpa pillow) |
| Database | SQLite |
| Manajemen sesi | Flask-Session |

## Struktur Proyek

```
Login-Aman/
├── app.py             # Application factory + route index
├── config.py          # Konfigurasi (secret, parameter keamanan)
├── db.py              # Koneksi SQLite + perintah init-db
├── schema.sql         # Skema tabel (users, login_attempts)
├── auth/
│   └── __init__.py    # Blueprint autentikasi (register/login/otp/dashboard/logout)
│       ├── security.py   # bcrypt, TOTP, QR (SVG), validasi input
│       └── audit.py      # audit log + rate limiting
├── templates/         # Halaman HTML (Jinja2)
├── static/css/        # Styling
├── tests/             # Suite pytest (TS-01..TS-10)
├── requirements.txt
├── requirements-dev.txt
└── instance/          # Database & sesi (dibuat otomatis, tidak di-commit)
```

## Cara Menjalankan (Pengembangan Lokal)

```bash
# 1. Buat & aktifkan virtual environment
python -m venv .venv
.venv\Scripts\activate        # Windows (PowerShell: .venv\Scripts\Activate.ps1)
# source .venv/bin/activate   # Linux/macOS

# 2. Pasang dependensi
pip install -r requirements.txt

# 3. Inisialisasi database (sekali)
flask --app app init-db

# 4. Jalankan server
flask --app app run --debug
```

Buka <http://127.0.0.1:5000>.

## Pengujian Otomatis

Suite `pytest` membuktikan skenario keamanan PRD Bab 9 (TS-01..TS-10) dan
kebutuhan fungsional secara otomatis — dapat dilampirkan sebagai bukti uji.

```bash
pip install -r requirements-dev.txt
pytest                 # 17 test, semua harus PASS
```

Pemetaan test → skenario PRD:

| Skenario / FR | Test |
|---|---|
| FR-01 / TS-02 hash bcrypt | `test_fr01_password_disimpan_sebagai_hash_bcrypt` |
| TS-03 salt unik | `test_ts03_password_sama_hash_berbeda` |
| FR-02 QR + secret | `test_fr02_qr_dan_secret_ditampilkan` |
| FR-06 validasi input | `test_fr06_password_pendek_ditolak`, `test_fr06_username_duplikat_ditolak` |
| TS-01 password salah / pesan generik | `test_ts01_password_salah_ditolak`, `test_ts01_pesan_generik_user_tidak_ada` |
| Alur sukses end-to-end | `test_alur_sukses_lengkap` |
| TS-04 OTP salah | `test_ts04_otp_salah_ditolak` |
| TS-05 OTP kadaluwarsa | `test_ts05_otp_kadaluwarsa_ditolak` |
| TS-06 dashboard tanpa login | `test_ts06_dashboard_tanpa_login_dialihkan` |
| TS-07 bypass OTP | `test_ts07_bypass_otp_ditolak` |
| TS-08 SQL injection | `test_ts08_sql_injection_login` |
| FR-07 logout | `test_fr07_logout_mengakhiri_sesi` |
| TS-10 / FR-09 anti-replay | `test_ts10_replay_otp_ditolak` |
| TS-09 / FR-08 rate limiting | `test_ts09_rate_limiting` |
| FR-10 audit log | `test_fr10_audit_log_tanpa_kredensial` |

## Status Pengerjaan (per PRD Bab 12)

- [x] **Fase 1 — Fondasi:** struktur proyek, koneksi DB, skema `users`, halaman dasar registrasi/login.
- [x] **Fase 2 — Autentikasi Inti:** FR-01..FR-05 + FR-07 (bcrypt, secret + QR SVG, login dua tahap, proteksi dashboard, logout) — terverifikasi 16/16 cek otomatis.
- [x] **Fase 3 — Pengerasan & fitur P1:** rate limiting (FR-08), anti-replay OTP (FR-09), audit log (FR-10), indikator kekuatan password (FR-11) — terverifikasi 8/8 cek otomatis. Sisa: dokumentasi screenshot TS-01..TS-10.
- [x] **Fase 4 — Dokumentasi:** draf laporan akhir ([LAPORAN.md](LAPORAN.md)) — isi teknis lengkap, tinggal sisipkan screenshot demo & data identitas.

> Logika keamanan ada di [auth/security.py](auth/security.py) (bcrypt, TOTP, QR, validasi)
> dan alur route di [auth/__init__.py](auth/__init__.py).
