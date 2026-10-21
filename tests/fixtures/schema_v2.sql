-- CrawlInsight — schema 2.0 / SRS section 7.4. UTC timestamps use ISO 8601 Z.
PRAGMA foreign_keys = ON;
PRAGMA journal_mode = WAL;
PRAGMA busy_timeout = 5000;

CREATE TABLE IF NOT EXISTS books (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_url TEXT NOT NULL UNIQUE,
    title TEXT NOT NULL CHECK(length(trim(title)) > 0),
    price_pence INTEGER NOT NULL CHECK (price_pence >= 0),
    rating INTEGER NOT NULL CHECK (rating BETWEEN 1 AND 5),
    category TEXT NOT NULL CHECK(length(trim(category)) > 0),
    availability TEXT NOT NULL CHECK(length(trim(availability)) > 0),
    image_url TEXT,
    upc TEXT,
    first_seen_at TEXT NOT NULL,
    last_seen_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS crawl_jobs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    max_pages INTEGER NOT NULL CHECK (max_pages BETWEEN 1 AND 3),
    status TEXT NOT NULL DEFAULT 'PENDING'
       CHECK(status IN ('PENDING', 'RUNNING', 'COMPLETED', 'FAILED')),
    catalogue_pages_done INTEGER NOT NULL DEFAULT 0,
    books_found INTEGER NOT NULL DEFAULT 0,
    items_saved INTEGER NOT NULL DEFAULT 0,
    new_books INTEGER NOT NULL DEFAULT 0,
    existing_books INTEGER NOT NULL DEFAULT 0,
    error_count INTEGER NOT NULL DEFAULT 0,
    last_error TEXT,
    created_at TEXT NOT NULL,
    started_at TEXT,
    finished_at TEXT,
    CHECK (items_saved = new_books + existing_books),
    CHECK (catalogue_pages_done >= 0),
    CHECK (books_found >= 0),
    CHECK (items_saved >= 0)
);

CREATE INDEX IF NOT EXISTS idx_books_title ON books(title);
CREATE INDEX IF NOT EXISTS idx_books_price ON books(price_pence);
CREATE INDEX IF NOT EXISTS idx_jobs_created ON crawl_jobs(id DESC);
