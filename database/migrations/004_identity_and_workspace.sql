-- 004_identity_and_workspace.sql - additive, non-destructive migration (SQLite)
-- Accounts and each person's saved workspace; shared books remain source records.
CREATE TABLE IF NOT EXISTS users (
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 full_name TEXT NOT NULL CHECK(length(trim(full_name)) BETWEEN 2 AND 100),
 email TEXT NOT NULL COLLATE NOCASE UNIQUE CHECK(length(email) BETWEEN 5 AND 254),
 password_hash TEXT NOT NULL,
 is_active INTEGER NOT NULL DEFAULT 1 CHECK(is_active IN (0,1)),
 session_version INTEGER NOT NULL DEFAULT 0 CHECK(session_version >= 0),
 created_at TEXT NOT NULL,
 updated_at TEXT NOT NULL,
 last_login_at TEXT
);
CREATE TABLE IF NOT EXISTS user_preferences (
 user_id INTEGER PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
 locale TEXT NOT NULL DEFAULT 'vi' CHECK(locale IN ('vi','en')),
 theme TEXT NOT NULL DEFAULT 'system' CHECK(theme IN ('light','dark','system')),
 book_layout TEXT NOT NULL DEFAULT 'grid' CHECK(book_layout IN ('grid','list')),
 updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS bookmarks (
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
 book_id INTEGER NOT NULL REFERENCES books(id) ON DELETE CASCADE,
 note TEXT NOT NULL DEFAULT '' CHECK(length(note) <= 500),
 created_at TEXT NOT NULL,
 UNIQUE(user_id,book_id)
);
CREATE TABLE IF NOT EXISTS saved_searches (
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
 name TEXT NOT NULL CHECK(length(trim(name)) BETWEEN 1 AND 60),
 query TEXT NOT NULL DEFAULT '' CHECK(length(query)<=100),
 min_price TEXT NOT NULL DEFAULT '' CHECK(length(min_price)<=12),
 max_price TEXT NOT NULL DEFAULT '' CHECK(length(max_price)<=12),
 created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS password_reset_tokens (
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
 token_hash TEXT NOT NULL UNIQUE,
 expires_at TEXT NOT NULL,
 used_at TEXT,
 created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS auth_attempts (
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 subject_hash TEXT NOT NULL,
 attempted_at TEXT NOT NULL,
 success INTEGER NOT NULL CHECK(success IN (0,1))
);
ALTER TABLE crawl_jobs ADD COLUMN user_id INTEGER REFERENCES users(id) ON DELETE SET NULL;
CREATE INDEX IF NOT EXISTS idx_crawl_jobs_user ON crawl_jobs(user_id,id DESC);
CREATE INDEX IF NOT EXISTS idx_bookmarks_user ON bookmarks(user_id,created_at DESC);
CREATE INDEX IF NOT EXISTS idx_saved_searches_user ON saved_searches(user_id,id DESC);
CREATE INDEX IF NOT EXISTS idx_reset_user_expiry ON password_reset_tokens(user_id,expires_at);
CREATE INDEX IF NOT EXISTS idx_attempts_subject_time ON auth_attempts(subject_hash,attempted_at);
