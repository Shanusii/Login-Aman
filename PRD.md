# Product Requirements Document

# Implementasi Sistem Login Aman Menggunakan OTP dan Hashing Password

| | |
|---|---|
| **Versi Dokumen** | 1.0 |
| **Status** | Draft — Untuk Review |
| **Tanggal** | 11 Juni 2026 |
| **Penyusun** | Shanusi |
| **Mata Kuliah** | Keamanan Informasi |
| **Jenis Proyek** | Tugas Akademik / Project |

---

## Daftar Isi

1. [Ringkasan Eksekutif](#1-ringkasan-eksekutif)
2. [Latar Belakang dan Pernyataan Masalah](#2-latar-belakang-dan-pernyataan-masalah)
3. [Tujuan (Goals)](#3-tujuan-goals)
4. [Di Luar Lingkup (Non-Goals)](#4-di-luar-lingkup-non-goals)
5. [Persona dan User Stories](#5-persona-dan-user-stories)
6. [Kebutuhan Fungsional](#6-kebutuhan-fungsional)
7. [Kebutuhan Non-Fungsional](#7-kebutuhan-non-fungsional)
8. [Arsitektur Sistem dan Desain Data](#8-arsitektur-sistem-dan-desain-data)
9. [Skenario Pengujian Keamanan](#9-skenario-pengujian-keamanan)
10. [Metrik Keberhasilan](#10-metrik-keberhasilan)
11. [Pertanyaan Terbuka](#11-pertanyaan-terbuka)
12. [Rencana dan Fase Pengerjaan](#12-rencana-dan-fase-pengerjaan)
13. [Glosarium](#13-glosarium)

---

## 1. Ringkasan Eksekutif

Dokumen ini mendefinisikan kebutuhan produk (Product Requirements Document) untuk pembangunan Sistem Login Aman berbasis autentikasi dua faktor (Two-Factor Authentication / 2FA). Sistem menggabungkan dua lapisan keamanan utama: (1) penyimpanan password menggunakan algoritma hashing **bcrypt** dengan salt otomatis, dan (2) verifikasi identitas tahap kedua menggunakan **One-Time Password (OTP)** berbasis waktu (TOTP) yang kompatibel dengan aplikasi authenticator standar seperti Google Authenticator.

Sistem ini dikembangkan sebagai proyek mata kuliah Keamanan Informasi dengan tujuan mendemonstrasikan praktik keamanan autentikasi modern secara fungsional, terukur, dan dapat diuji. Hasil akhir berupa aplikasi web yang dapat dijalankan dan didemonstrasikan, lengkap dengan skenario pengujian keamanan yang terdokumentasi.

---

## 2. Latar Belakang dan Pernyataan Masalah

### 2.1 Latar Belakang

Autentikasi berbasis username dan password tunggal merupakan mekanisme paling umum sekaligus paling rentan dalam sistem informasi. Dua kelemahan utamanya adalah: pertama, kebocoran database yang menyimpan password dalam bentuk teks asli (plaintext) atau hash lemah (MD5/SHA-1) memungkinkan penyerang membaca seluruh kredensial pengguna; kedua, password yang dicuri melalui phishing, keylogger, atau credential stuffing dapat langsung digunakan untuk mengambil alih akun tanpa hambatan tambahan.

### 2.2 Pernyataan Masalah

Sistem login konvensional satu faktor tidak memberikan perlindungan memadai terhadap dua vektor serangan utama: kompromi database dan kompromi kredensial. Dibutuhkan sistem autentikasi yang (a) memastikan password tidak pernah tersimpan maupun terbaca dalam bentuk asli, dan (b) menambahkan faktor verifikasi kedua yang bersifat dinamis dan terikat waktu sehingga kredensial curian saja tidak cukup untuk masuk ke dalam sistem.

### 2.3 Dampak Jika Tidak Diselesaikan

- Kebocoran satu database berarti kebocoran seluruh password pengguna dalam bentuk yang dapat dieksploitasi.
- Akun pengguna dapat diambil alih hanya dengan satu kredensial bocor (single point of failure).
- Sistem tidak memenuhi standar praktik keamanan industri (OWASP ASVS, NIST SP 800-63B) yang merekomendasikan hashing adaptif dan autentikasi multifaktor.

---

## 3. Tujuan (Goals)

Tujuan berikut bersifat terukur dan menjadi acuan keberhasilan proyek:

1. **Keamanan penyimpanan:** 100% password pengguna tersimpan sebagai hash bcrypt (cost factor ≥ 12) — tidak ada satu pun password plaintext di database, log, maupun respons API.
2. **Autentikasi dua faktor fungsional:** 100% proses login mewajibkan verifikasi TOTP yang valid setelah password benar; tidak ada jalur pintas (bypass) menuju sesi terautentikasi.
3. **Ketahanan terhadap serangan dasar:** Seluruh skenario pengujian keamanan (Bab 9) lulus, termasuk penolakan password salah, OTP kadaluwarsa, dan OTP yang dipakai ulang.
4. **Kompatibilitas standar:** Implementasi TOTP sesuai RFC 6238 dan dapat dipindai oleh Google Authenticator melalui QR code (format `otpauth://`).
5. **Kesiapan demonstrasi:** Alur registrasi hingga login lengkap dapat didemonstrasikan end-to-end dalam waktu kurang dari 5 menit.

---

## 4. Di Luar Lingkup (Non-Goals)

Hal-hal berikut secara eksplisit tidak termasuk dalam lingkup versi 1.0, untuk menjaga fokus dan kelayakan waktu pengerjaan:

1. **OTP melalui SMS atau email.** Membutuhkan integrasi layanan pihak ketiga (gateway SMS/SMTP) berbayar; TOTP via authenticator app sudah cukup untuk mendemonstrasikan konsep 2FA dan lebih aman dari SMS.
2. **Login sosial (OAuth/Google/GitHub).** Berbeda topik dari fokus proyek, yaitu hashing dan OTP buatan sendiri.
3. **Fitur lupa password / reset password.** Alur reset yang aman adalah topik kompleks tersendiri; dicatat sebagai pengembangan masa depan (P2).
4. **Manajemen peran dan otorisasi (RBAC).** Proyek fokus pada autentikasi (siapa Anda), bukan otorisasi (apa yang boleh Anda lakukan).
5. **Deployment produksi dan HTTPS publik.** Sistem dijalankan di lingkungan lokal/laboratorium untuk keperluan demonstrasi akademik.

---

## 5. Persona dan User Stories

### 5.1 Persona

| Persona | Deskripsi | Kebutuhan Utama |
|---|---|---|
| Pengguna Akhir | Mahasiswa/karyawan yang mendaftar dan login ke sistem. | Proses registrasi dan login yang aman namun tetap mudah diikuti. |
| Administrator / Penguji | Dosen atau penguji yang memverifikasi keamanan sistem. | Bukti bahwa password ter-hash dan 2FA tidak dapat dilewati. |
| Penyerang (ancaman) | Aktor jahat yang mencoba menembus sistem. | Persona negatif — sistem harus menggagalkan setiap upayanya. |

### 5.2 User Stories

Diurutkan berdasarkan prioritas:

- **US-01:** Sebagai pengguna baru, saya ingin mendaftar dengan username dan password agar memiliki akun pada sistem.
- **US-02:** Sebagai pengguna baru, saya ingin memindai QR code dengan aplikasi authenticator agar perangkat saya menjadi faktor kedua autentikasi.
- **US-03:** Sebagai pengguna terdaftar, saya ingin login dengan password lalu kode OTP agar akun saya terlindungi meskipun password saya bocor.
- **US-04:** Sebagai pengguna, saya ingin pesan kesalahan yang jelas (tanpa membocorkan informasi sensitif) saat login gagal, agar saya tahu harus berbuat apa.
- **US-05:** Sebagai penguji, saya ingin melihat isi tabel pengguna di database agar dapat memverifikasi bahwa password tersimpan sebagai hash bcrypt, bukan plaintext.
- **US-06:** Sebagai pengguna yang sudah login, saya ingin mengakses halaman dashboard yang terproteksi agar mendapat bukti sesi saya valid.
- **US-07:** Sebagai pengguna, saya ingin logout agar sesi saya berakhir dan tidak dapat disalahgunakan orang lain.

---

## 6. Kebutuhan Fungsional

### 6.1 Wajib Ada — Prioritas P0

Sistem tidak layak dirilis/didemokan tanpa kebutuhan berikut:

| Kode | Kebutuhan | Kriteria Penerimaan (Acceptance Criteria) |
|---|---|---|
| FR-01 | Registrasi akun dengan hashing bcrypt | Diberikan form registrasi; ketika pengguna submit username unik dan password valid; maka password di-hash dengan bcrypt (salt otomatis, cost ≥ 12) sebelum disimpan, dan tidak ada plaintext yang tercatat di mana pun. |
| FR-02 | Pembuatan secret TOTP saat registrasi | Diberikan registrasi berhasil; ketika akun dibuat; maka sistem membuat secret TOTP unik (base32) dan menampilkan QR code format `otpauth://` yang dapat dipindai Google Authenticator. |
| FR-03 | Login tahap 1 — verifikasi password | Diberikan akun terdaftar; ketika pengguna memasukkan username + password; maka sistem memverifikasi dengan fungsi compare bcrypt. Password salah → ditolak dengan pesan generik; benar → lanjut tahap OTP tanpa membuat sesi penuh. |
| FR-04 | Login tahap 2 — verifikasi TOTP | Diberikan password tervalidasi; ketika pengguna memasukkan kode 6 digit; maka sistem memverifikasi terhadap secret pengguna (window 30 detik). Kode salah/kadaluwarsa → ditolak; valid → sesi login dibuat. |
| FR-05 | Proteksi halaman dashboard | Diberikan pengguna belum menyelesaikan kedua tahap login; ketika mengakses URL dashboard secara langsung; maka sistem mengalihkan ke halaman login (tidak ada akses tanpa sesi valid). |
| FR-06 | Validasi input | Username dan password divalidasi (panjang minimum password 8 karakter; username unik). Input dikirim ke database melalui parameterized query untuk mencegah SQL injection. |
| FR-07 | Logout | Diberikan pengguna login; ketika menekan tombol logout; maka sesi dihapus di sisi server dan akses dashboard berikutnya ditolak. |

### 6.2 Sebaiknya Ada — Prioritas P1

| Kode | Kebutuhan | Kriteria Penerimaan |
|---|---|---|
| FR-08 | Pembatasan percobaan login (rate limiting) | Setelah 5 kali kegagalan beruntun dalam 15 menit, akun/IP ditunda sementara untuk memperlambat serangan brute force. |
| FR-09 | Pencegahan pemakaian ulang OTP (replay) | Kode OTP yang sudah berhasil dipakai pada satu window waktu tidak dapat digunakan kembali pada window yang sama. |
| FR-10 | Log aktivitas autentikasi | Setiap percobaan login (berhasil/gagal) tercatat dengan timestamp dan username — tanpa mencatat password maupun kode OTP. |
| FR-11 | Indikator kekuatan password | Form registrasi menampilkan indikator kekuatan password secara real-time untuk mendorong password yang baik. |

### 6.3 Pertimbangan Masa Depan — Prioritas P2

- Kode cadangan (backup codes) untuk pemulihan saat perangkat authenticator hilang.
- Alur reset password yang aman berbasis token sekali pakai via email.
- Dukungan WebAuthn/passkey sebagai faktor alternatif.
- Notifikasi login dari perangkat baru.

> Catatan: skema database dirancang agar penambahan kolom untuk fitur di atas tidak memerlukan migrasi besar.

---

## 7. Kebutuhan Non-Fungsional

| Kategori | Kebutuhan |
|---|---|
| Keamanan | Bcrypt cost factor ≥ 12; secret TOTP minimal 160 bit; perbandingan kredensial menggunakan fungsi constant-time bawaan library; pesan kesalahan login bersifat generik (tidak membedakan "username tidak ada" vs "password salah"); session cookie ber-flag HttpOnly. |
| Kinerja | Verifikasi bcrypt + TOTP selesai < 1 detik per percobaan login pada perangkat pengembangan standar. |
| Usabilitas | Alur registrasi hingga login pertama dapat diselesaikan pengguna awam dalam < 3 menit dengan instruksi pada layar. |
| Portabilitas | Sistem berjalan di lingkungan lokal (Windows/Linux/macOS) hanya dengan menginstal dependensi yang terdokumentasi. |
| Keterujian | Setiap kebutuhan P0 memiliki skenario uji yang dapat dijalankan dan didokumentasikan (Bab 9). |

---

## 8. Arsitektur Sistem dan Desain Data

### 8.1 Komponen Sistem

| Komponen | Teknologi (Opsi Python) | Teknologi (Opsi Node.js) |
|---|---|---|
| Framework web | Flask | Express |
| Hashing password | bcrypt | bcryptjs |
| OTP (TOTP, RFC 6238) | pyotp | otplib |
| QR code | qrcode + pillow | qrcode |
| Database | SQLite (built-in sqlite3) | SQLite (better-sqlite3) |
| Manajemen sesi | flask-session | express-session |

### 8.2 Alur Utama

**Alur Registrasi**

Pengguna mengisi username + password → sistem memvalidasi input → password di-hash dengan bcrypt → sistem membuat secret TOTP → username, hash, dan secret disimpan ke database → QR code ditampilkan → pengguna memindai dengan Google Authenticator.

**Alur Login (Dua Tahap)**

- *Tahap 1:* pengguna memasukkan username + password → sistem mengambil hash dari database → bcrypt compare → jika cocok, status "menunggu OTP" disimpan sementara (belum login penuh).
- *Tahap 2:* pengguna memasukkan kode 6 digit dari authenticator → sistem memverifikasi terhadap secret (window 30 detik) → jika valid, sesi login dibuat → pengguna diarahkan ke dashboard.

### 8.3 Skema Database

Tabel utama: `users`

```sql
CREATE TABLE users (
  id            INTEGER PRIMARY KEY AUTOINCREMENT,
  username      TEXT UNIQUE NOT NULL,
  password_hash TEXT NOT NULL,      -- hash bcrypt, ±60 karakter
  totp_secret   TEXT NOT NULL,      -- secret base32
  created_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

Tabel pendukung (P1): `login_attempts` untuk rate limiting dan audit log, berisi kolom username, status (sukses/gagal), tahap (password/otp), dan timestamp.

---

## 9. Skenario Pengujian Keamanan

Skenario berikut wajib dijalankan dan hasilnya didokumentasikan (tangkapan layar) sebagai bukti pada laporan/presentasi:

| Kode | Skenario | Hasil yang Diharapkan |
|---|---|---|
| TS-01 | Login dengan password salah | Akses ditolak; pesan kesalahan generik; tidak lanjut ke tahap OTP. |
| TS-02 | Inspeksi langsung tabel users di database | Kolom password berisi hash bcrypt (diawali `$2b$...`), bukan teks asli. |
| TS-03 | Dua akun dengan password sama | Hash yang tersimpan berbeda (bukti salt unik per pengguna). |
| TS-04 | Memasukkan kode OTP salah | Akses ditolak; sesi tidak terbentuk. |
| TS-05 | Memasukkan kode OTP yang sudah kadaluwarsa (> 30 detik) | Akses ditolak. |
| TS-06 | Mengakses URL dashboard tanpa login | Dialihkan ke halaman login; konten terproteksi tidak bocor. |
| TS-07 | Melewati tahap OTP dengan mengakses dashboard setelah tahap 1 saja | Ditolak — status "menunggu OTP" bukan sesi penuh. |
| TS-08 | Percobaan SQL injection pada form login (mis. `' OR 1=1 --`) | Input diperlakukan sebagai data biasa; login gagal; tidak ada error database. |
| TS-09 | (P1) 5+ percobaan login gagal beruntun | Percobaan berikutnya ditunda sementara (rate limiting aktif). |
| TS-10 | (P1) Menggunakan ulang kode OTP yang baru berhasil dipakai | Ditolak (proteksi replay). |

---

## 10. Metrik Keberhasilan

### 10.1 Indikator Utama

| Metrik | Target | Cara Pengukuran |
|---|---|---|
| Skenario uji P0 (TS-01 s.d. TS-08) lulus | 8/8 (100%) | Eksekusi manual + dokumentasi tangkapan layar |
| Password plaintext di database/log | 0 temuan | Inspeksi database dan file log |
| Jalur bypass menuju dashboard | 0 jalur | Pengujian akses langsung URL |
| Waktu demonstrasi end-to-end | < 5 menit | Uji coba demo sebelum presentasi |
| Kompatibilitas QR dengan Google Authenticator | Berhasil dipindai | Uji pada perangkat nyata |

---

## 11. Pertanyaan Terbuka

| Pertanyaan | Pemilik Jawaban |
|---|---|
| Apakah deliverable wajib berupa aplikasi web, atau prototipe CLI diperbolehkan? | Dosen pengampu (blocking) |
| Apakah proyek dikerjakan individu atau kelompok, dan adakah pembagian peran? | Dosen / tim (blocking) |
| Stack final: Python (Flask) atau Node.js (Express)? | Pengembang (blocking) |
| Apakah fitur P1 (rate limiting, anti-replay) dibutuhkan untuk nilai, atau cukup P0? | Dosen pengampu (non-blocking) |
| Format laporan akhir: dokumen, presentasi, atau keduanya? | Dosen pengampu (non-blocking) |

---

## 12. Rencana dan Fase Pengerjaan

Estimasi total: 3–4 minggu kalender (dapat disesuaikan dengan tenggat tugas).

1. **Fase 1 — Fondasi (Minggu 1):** Setup proyek, struktur folder, koneksi database, skema tabel users, halaman dasar (registrasi/login).
2. **Fase 2 — Autentikasi Inti (Minggu 2):** Implementasi FR-01 s.d. FR-05: hashing bcrypt, pembuatan secret + QR code, login dua tahap, proteksi dashboard, logout.
3. **Fase 3 — Pengerasan & Pengujian (Minggu 3):** Validasi input, eksekusi seluruh skenario TS-01 s.d. TS-08, perbaikan temuan, fitur P1 jika waktu memungkinkan.
4. **Fase 4 — Dokumentasi & Demo (Minggu 4):** Penyusunan laporan/presentasi, dokumentasi hasil uji, gladi resik demonstrasi.

> Dependensi: ketersediaan perangkat dengan aplikasi authenticator untuk pengujian; jawaban atas pertanyaan terbuka yang bersifat blocking sebelum Fase 2 dimulai.

---

## 13. Glosarium

| Istilah | Definisi |
|---|---|
| 2FA | Two-Factor Authentication — autentikasi yang mewajibkan dua bukti identitas berbeda (sesuatu yang diketahui + sesuatu yang dimiliki). |
| Bcrypt | Algoritma hashing password adaptif dengan salt bawaan dan cost factor yang dapat dinaikkan seiring perkembangan perangkat keras. |
| Salt | Data acak unik yang dicampurkan ke password sebelum hashing agar dua password sama menghasilkan hash berbeda dan rainbow table tidak efektif. |
| Cost factor | Parameter bcrypt yang menentukan jumlah iterasi; semakin besar, semakin lambat dihitung (mempersulit brute force). |
| OTP | One-Time Password — kode sekali pakai yang hanya berlaku singkat. |
| TOTP | Time-based OTP (RFC 6238) — OTP yang dihitung dari secret bersama dan waktu saat ini, berganti setiap 30 detik. |
| Secret TOTP | Kunci rahasia (base32) yang dibagikan sekali antara server dan aplikasi authenticator pengguna melalui QR code. |
| Replay attack | Serangan dengan memakai ulang kredensial/kode yang pernah berhasil digunakan. |
| Rate limiting | Pembatasan jumlah percobaan dalam rentang waktu tertentu untuk memperlambat serangan brute force. |
| Session | Status login yang disimpan server setelah autentikasi berhasil, direferensikan oleh cookie pada browser pengguna. |