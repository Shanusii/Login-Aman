-- Skema database Sistem Login Aman (SQLite)
-- Sesuai PRD Bab 8.3

-- Tabel utama pengguna.
CREATE TABLE IF NOT EXISTS users (
  id            INTEGER PRIMARY KEY AUTOINCREMENT,
  username      TEXT UNIQUE NOT NULL,
  password_hash TEXT NOT NULL,      -- hash bcrypt, +-60 karakter, diawali $2b$
  totp_secret   TEXT NOT NULL,      -- secret base32 (>= 160 bit)
  last_totp_counter INTEGER NOT NULL DEFAULT 0,  -- window TOTP terakhir dipakai (anti-replay, FR-09)
  created_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Tabel pendukung (P1): audit log + dasar rate limiting.
-- Tidak pernah menyimpan password maupun kode OTP.
CREATE TABLE IF NOT EXISTS login_attempts (
  id         INTEGER PRIMARY KEY AUTOINCREMENT,
  username   TEXT,
  status     TEXT NOT NULL,         -- 'sukses' | 'gagal'
  stage      TEXT NOT NULL,         -- 'password' | 'otp'
  ip_address TEXT,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_login_attempts_username
  ON login_attempts (username, created_at);
