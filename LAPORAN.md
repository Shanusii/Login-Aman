# Laporan Proyek
# Implementasi Sistem Login Aman Menggunakan OTP dan Hashing Password

| | |
|---|---|
| **Mata Kuliah** | Keamanan Informasi |
| **Penyusun** | _(nama / NIM)_ |
| **Dosen Pengampu** | _(nama dosen)_ |
| **Tanggal** | _(isi tanggal pengumpulan)_ |

> Catatan pengisian: bagian bertanda _(…)_ dan blok **[Sisipkan tangkapan layar]**
> dilengkapi sebelum dikumpulkan. Seluruh klaim pengujian pada Bab 6 sudah
> dibuktikan otomatis oleh suite `pytest` (17 test lulus) — tangkapan layar
> demo manual berfungsi sebagai bukti visual pendamping.

---

## Daftar Isi

1. [Pendahuluan](#1-pendahuluan)
2. [Dasar Teori](#2-dasar-teori)
3. [Analisis dan Perancangan](#3-analisis-dan-perancangan)
4. [Implementasi](#4-implementasi)
5. [Cara Menjalankan](#5-cara-menjalankan)
6. [Pengujian Keamanan](#6-pengujian-keamanan)
7. [Pembahasan](#7-pembahasan)
8. [Kesimpulan dan Saran](#8-kesimpulan-dan-saran)
9. [Daftar Pustaka](#9-daftar-pustaka)

---

## 1. Pendahuluan

### 1.1 Latar Belakang

Autentikasi berbasis username dan password tunggal merupakan mekanisme yang
paling umum sekaligus paling rentan. Dua kelemahan utamanya: (1) kebocoran
database yang menyimpan password dalam bentuk plaintext atau hash lemah
(MD5/SHA-1) membuka seluruh kredensial pengguna, dan (2) password yang dicuri
melalui phishing atau credential stuffing dapat langsung dipakai mengambil alih
akun tanpa hambatan tambahan.

Proyek ini membangun sistem login yang menutup kedua celah tersebut dengan
menggabungkan **hashing password adaptif (bcrypt)** dan **autentikasi dua
faktor berbasis TOTP (Time-based One-Time Password)**.

### 1.2 Rumusan Masalah

1. Bagaimana memastikan password tidak pernah tersimpan maupun terbaca dalam
   bentuk asli, bahkan jika database bocor?
2. Bagaimana menambahkan faktor verifikasi kedua yang dinamis dan terikat waktu
   sehingga kredensial curian saja tidak cukup untuk masuk?
3. Bagaimana membuktikan secara terukur bahwa sistem tahan terhadap serangan
   dasar (password salah, OTP kadaluwarsa/replay, bypass sesi, SQL injection)?

### 1.3 Tujuan

1. 100% password tersimpan sebagai hash bcrypt (cost ≥ 12) — nol plaintext.
2. 100% login mewajibkan verifikasi TOTP valid; tidak ada jalur bypass.
3. Seluruh skenario pengujian keamanan (Bab 6) lulus.
4. Implementasi TOTP sesuai RFC 6238 dan kompatibel Google Authenticator.

### 1.4 Batasan Masalah

Mengikuti Non-Goals PRD: tanpa OTP via SMS/email, tanpa login sosial (OAuth),
tanpa reset password, tanpa RBAC, dan dijalankan di lingkungan lokal (bukan
deployment produksi/HTTPS publik).

---

## 2. Dasar Teori

### 2.1 Hashing Password dan Bcrypt

*Hashing* adalah transformasi satu arah: dari password mudah menghitung hash,
tetapi dari hash secara praktis mustahil mengembalikan password. **Bcrypt**
adalah algoritma hashing adaptif yang memiliki dua sifat penting:

- **Salt otomatis** — data acak unik dicampurkan ke setiap password sebelum
  di-hash, sehingga dua pengguna dengan password sama menghasilkan hash berbeda
  dan *rainbow table* tidak efektif.
- **Cost factor** — jumlah iterasi dapat dinaikkan seiring perkembangan
  perangkat keras; semakin besar cost, semakin lambat dihitung, mempersulit
  serangan brute force. Proyek ini memakai **cost = 12**.

Hash bcrypt berformat `$2b$<cost>$<22-char-salt><31-char-hash>` (±60 karakter).

### 2.2 OTP dan TOTP (RFC 6238)

**OTP** adalah kode sekali pakai yang berlaku singkat. **TOTP** menurunkan kode
tersebut dari dua masukan: sebuah *secret* yang dibagikan sekali antara server
dan perangkat pengguna, serta *waktu saat ini* yang dibagi menjadi *window*
30 detik. Karena server dan aplikasi authenticator (mis. Google Authenticator)
memegang secret yang sama dan jam yang tersinkron, keduanya menghitung kode 6
digit yang sama tanpa perlu komunikasi. Secret dibagikan via **QR code** dengan
URI `otpauth://`.

### 2.3 Autentikasi Dua Faktor (2FA)

2FA mewajibkan dua bukti identitas dari kategori berbeda: *sesuatu yang
diketahui* (password) dan *sesuatu yang dimiliki* (perangkat berisi secret
TOTP). Dengan demikian, password yang bocor saja tidak cukup untuk masuk.

### 2.4 Ancaman yang Ditangani

| Ancaman | Mitigasi pada sistem ini |
|---|---|
| Kebocoran database | Password hanya disimpan sebagai hash bcrypt + salt |
| Kredensial curian | Faktor kedua TOTP yang dinamis dan terikat waktu |
| Brute force | Cost factor bcrypt + rate limiting |
| Replay OTP | Pencatatan window TOTP terakhir yang dipakai |
| SQL injection | Parameterized query di seluruh akses database |
| Enumerasi user | Pesan kesalahan login yang generik |
| Pencurian sesi via XSS | Session cookie ber-flag HttpOnly |

---

## 3. Analisis dan Perancangan

### 3.1 Kebutuhan Fungsional

| Kode | Kebutuhan | Prioritas |
|---|---|---|
| FR-01 | Registrasi dengan hashing bcrypt | P0 |
| FR-02 | Pembuatan secret TOTP + QR code saat registrasi | P0 |
| FR-03 | Login tahap 1 — verifikasi password | P0 |
| FR-04 | Login tahap 2 — verifikasi TOTP | P0 |
| FR-05 | Proteksi halaman dashboard | P0 |
| FR-06 | Validasi input + parameterized query | P0 |
| FR-07 | Logout | P0 |
| FR-08 | Rate limiting | P1 |
| FR-09 | Pencegahan replay OTP | P1 |
| FR-10 | Log aktivitas autentikasi | P1 |
| FR-11 | Indikator kekuatan password | P1 |

Seluruh FR di atas telah diimplementasikan.

### 3.2 Arsitektur dan Teknologi

| Komponen | Teknologi |
|---|---|
| Framework web | Flask |
| Hashing password | bcrypt (cost 12) |
| OTP (TOTP, RFC 6238) | pyotp |
| QR code | qrcode (keluaran **SVG**, tanpa pillow) |
| Database | SQLite |
| Manajemen sesi | Flask-Session (cookie HttpOnly) |

> **Catatan teknis:** PRD menyebut opsi `qrcode + pillow`. Pada lingkungan uji
> (Python 3.14, Windows) pillow tidak menyediakan *prebuilt wheel* dan gagal
> dikompilasi dari sumber. QR code karena itu dihasilkan sebagai **SVG murni
> Python** dan ditanam langsung ke HTML — lebih ringan, tanpa dependensi biner,
> dan tetap memenuhi FR-02.

### 3.3 Alur Sistem

**Registrasi:** pengguna mengisi username + password → validasi input →
password di-hash bcrypt → secret TOTP dibuat → username, hash, secret disimpan →
QR code ditampilkan → pengguna memindai dengan authenticator.

**Login dua tahap:**
- *Tahap 1* — username + password → bcrypt compare. Jika cocok, status
  "menunggu OTP" disimpan sementara (**belum** sesi penuh).
- *Tahap 2* — kode 6 digit → diverifikasi terhadap secret (window 30 detik) →
  jika valid, sesi penuh dibuat dan pengguna diarahkan ke dashboard.

```
[Registrasi] --hash+secret--> [DB] --QR--> [Authenticator]

[Login]
  username+password --bcrypt compare--> (gagal) --> tolak (pesan generik)
                                       \--(cocok)--> status "menunggu OTP"
  kode OTP --verifikasi TOTP--> (gagal) --> tolak
                               \--(valid)--> SESI PENUH --> Dashboard
```

### 3.4 Skema Database

```sql
CREATE TABLE users (
  id                INTEGER PRIMARY KEY AUTOINCREMENT,
  username          TEXT UNIQUE NOT NULL,
  password_hash     TEXT NOT NULL,      -- hash bcrypt, diawali $2b$
  totp_secret       TEXT NOT NULL,      -- secret base32 (>= 160 bit)
  last_totp_counter INTEGER NOT NULL DEFAULT 0,  -- anti-replay (FR-09)
  created_at        TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE login_attempts (   -- audit log + rate limiting (FR-08, FR-10)
  id         INTEGER PRIMARY KEY AUTOINCREMENT,
  username   TEXT,
  status     TEXT NOT NULL,     -- 'sukses' | 'gagal'
  stage      TEXT NOT NULL,     -- 'password' | 'otp'
  ip_address TEXT,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

Tabel `login_attempts` **tidak pernah** menyimpan password maupun kode OTP.

---

## 4. Implementasi

### 4.1 Struktur Proyek

```
Login-Aman/
├── app.py             # Application factory + route index
├── config.py          # Konfigurasi & parameter keamanan
├── db.py              # Koneksi SQLite + perintah init-db + migrasi
├── schema.sql         # Skema tabel
├── auth/
│   ├── __init__.py    # Route: register, login, login_otp, dashboard, logout
│   ├── security.py    # bcrypt, TOTP, QR (SVG), validasi input
│   └── audit.py       # audit log + rate limiting
├── templates/         # Halaman HTML (Jinja2)
├── static/css/        # Styling + indikator kekuatan password
└── tests/             # Suite pytest (TS-01..TS-10)
```

### 4.2 Cuplikan Kode Kunci

**Hashing & verifikasi password (FR-01, `auth/security.py`):**

```python
def hash_password(plain: str) -> str:
    cost = current_app.config["BCRYPT_COST"]            # 12
    digest = bcrypt.hashpw(plain.encode(), bcrypt.gensalt(rounds=cost))
    return digest.decode()

def verify_password(plain: str, password_hash: str) -> bool:
    return bcrypt.checkpw(plain.encode(), password_hash.encode())  # constant-time
```

**Pesan generik & login dua tahap (FR-03, `auth/__init__.py`):**

```python
if user is None or not security.verify_password(password, user["password_hash"]):
    audit.log_attempt(username, "gagal", "password")
    flash("Username atau password salah.", "error")   # pesan generik
    return render_template("login.html", username=username)
# sukses: simpan status "menunggu OTP" — BUKAN sesi penuh
session["pending_user_id"] = user["id"]
```

**Anti-replay TOTP (FR-09, `auth/__init__.py`):**

```python
counter = security.matched_totp_counter(user["totp_secret"], code)
if counter is None or counter <= user["last_totp_counter"]:
    ...  # tolak: salah, kadaluwarsa, atau sudah dipakai
db.execute("UPDATE users SET last_totp_counter = ? WHERE id = ?",
           (counter, user["id"]))   # kode tak bisa dipakai ulang
```

**Proteksi dashboard (FR-05):**

```python
@bp.route("/dashboard")
@login_required          # menolak akses bila session['user_id'] kosong
def dashboard(): ...
```

---

## 5. Cara Menjalankan

```bash
python -m venv .venv
.venv\Scripts\activate            # Windows
pip install -r requirements.txt
flask --app app init-db           # inisialisasi database (sekali)
flask --app app run --debug       # http://127.0.0.1:5000
```

Langkah demo: **Daftar** akun → **pindai QR** dengan Google Authenticator →
**Login** dengan password lalu kode 6 digit → masuk **Dashboard** → **Logout**.

---

## 6. Pengujian Keamanan

Pengujian dilakukan dua lapis: (a) **otomatis** dengan `pytest` (17 test, semua
lulus) dan (b) **manual** untuk bukti visual. Jalankan otomatis:

```bash
pip install -r requirements-dev.txt
pytest
```

**[Sisipkan tangkapan layar: hasil `pytest` — 17 passed]**

### 6.1 Tabel Hasil Pengujian

| Kode | Skenario | Hasil Diharapkan | Status | Bukti |
|---|---|---|---|---|
| TS-01 | Login dengan password salah | Ditolak, pesan generik, tidak ke OTP | ✅ Lulus | _(screenshot)_ |
| TS-02 | Inspeksi tabel `users` | Kolom password berisi hash `$2b$…` | ✅ Lulus | _(screenshot)_ |
| TS-03 | Dua akun password sama | Hash tersimpan berbeda (salt unik) | ✅ Lulus | _(screenshot)_ |
| TS-04 | Kode OTP salah | Ditolak, sesi tidak terbentuk | ✅ Lulus | _(screenshot)_ |
| TS-05 | Kode OTP kadaluwarsa (>30 dtk) | Ditolak | ✅ Lulus | _(screenshot)_ |
| TS-06 | Akses dashboard tanpa login | Dialihkan ke login | ✅ Lulus | _(screenshot)_ |
| TS-07 | Bypass OTP setelah tahap-1 saja | Ditolak | ✅ Lulus | _(screenshot)_ |
| TS-08 | SQL injection `' OR 1=1 --` | Diperlakukan data biasa; login gagal | ✅ Lulus | _(screenshot)_ |
| TS-09 | 5+ login gagal beruntun | Percobaan berikutnya ditunda | ✅ Lulus | _(screenshot)_ |
| TS-10 | Pakai ulang OTP yang sukses | Ditolak (anti-replay) | ✅ Lulus | _(screenshot)_ |

### 6.2 Bukti Tangkapan Layar (Demo Manual)

> Lengkapi blok berikut dengan tangkapan layar dari menjalankan aplikasi.

**a. Halaman registrasi + indikator kekuatan password (FR-11)**
**[Sisipkan tangkapan layar]**

**b. QR code hasil registrasi (FR-02)**
**[Sisipkan tangkapan layar]**

**c. Isi tabel `users` di DB — kolom password berupa hash `$2b$…` (TS-02, TS-03)**
**[Sisipkan tangkapan layar]**
Perintah inspeksi:
```bash
sqlite3 instance/app.db "SELECT username, password_hash FROM users;"
```

**d. Login password salah → pesan generik (TS-01)**
**[Sisipkan tangkapan layar]**

**e. Halaman input OTP & OTP salah ditolak (TS-04)**
**[Sisipkan tangkapan layar]**

**f. Login berhasil → Dashboard (FR-04)**
**[Sisipkan tangkapan layar]**

**g. Akses `/dashboard` tanpa login → dialihkan (TS-06)**
**[Sisipkan tangkapan layar]**

**h. Audit log `login_attempts` (FR-10)**
**[Sisipkan tangkapan layar]**
```bash
sqlite3 instance/app.db "SELECT username,status,stage,created_at FROM login_attempts;"
```

---

## 7. Pembahasan

- **Penyimpanan password (TS-02, TS-03):** seluruh password tersimpan sebagai
  hash bcrypt diawali `$2b$`. Dua akun dengan password identik tetap memiliki
  hash berbeda, membuktikan salt unik per pengguna bekerja sebagaimana mestinya.
- **Dua faktor tanpa bypass (TS-06, TS-07):** dashboard hanya dapat diakses
  setelah kedua tahap selesai. Status "menunggu OTP" sengaja dipisahkan dari
  sesi penuh, sehingga melewati tahap OTP tidak memberi akses.
- **Ketahanan OTP (TS-04, TS-05, TS-10):** kode salah, kode dari window lampau,
  maupun kode yang sudah pernah berhasil dipakai semuanya ditolak. Anti-replay
  diwujudkan dengan menyimpan nomor window terakhir yang berhasil.
- **Input tidak tepercaya (TS-08):** semua query memakai parameterized query,
  sehingga payload SQL injection diperlakukan sebagai string biasa.
- **Memperlambat brute force (TS-09):** setelah 5 kegagalan beruntun dalam 15
  menit, percobaan berikutnya ditunda — bahkan untuk password yang benar.

**Keterbatasan:** rate limiting berbasis catatan database sederhana (cocok untuk
skala demonstrasi); secret TOTP tersimpan tanpa enkripsi tambahan di sisi server
(umum untuk implementasi TOTP, namun di produksi sebaiknya dienkripsi/di-vault).

---

## 8. Kesimpulan dan Saran

### 8.1 Kesimpulan

Sistem login aman berhasil dibangun dan memenuhi seluruh tujuan proyek. Password
tidak pernah disimpan dalam bentuk asli (100% hash bcrypt cost 12), setiap login
mewajibkan faktor kedua TOTP tanpa jalur bypass, dan seluruh skenario pengujian
keamanan TS-01 s.d. TS-10 lulus — dibuktikan oleh 17 test otomatis sekaligus
demonstrasi manual.

### 8.2 Saran Pengembangan (P2)

- Kode cadangan (*backup codes*) untuk pemulihan saat perangkat authenticator
  hilang.
- Alur reset password aman berbasis token sekali pakai via email.
- Dukungan WebAuthn/passkey sebagai faktor alternatif.
- Enkripsi secret TOTP saat *at rest* dan deployment di belakang HTTPS.

---

## 9. Daftar Pustaka

1. Provos, N. & Mazières, D. (1999). *A Future-Adaptable Password Scheme* (bcrypt).
2. M'Raihi, D. dkk. (2011). *RFC 6238 — TOTP: Time-Based One-Time Password Algorithm.* IETF.
3. OWASP. *Application Security Verification Standard (ASVS).*
4. NIST. *SP 800-63B — Digital Identity Guidelines: Authentication and Lifecycle Management.*
5. Pallets Projects. *Flask Documentation.* https://flask.palletsprojects.com/
