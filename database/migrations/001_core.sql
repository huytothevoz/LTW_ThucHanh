-- 001_core.sql | CrawlInsight database v3 | SQLite 3.35+
-- Source of truth for persisted tables. Runtime data starts EMPTY.
-- Price is stored in integer GBP pennies (pence); UTC dates are ISO 8601 strings.
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS schema_migrations (
    version INTEGER PRIMARY KEY CHECK(version >= 1),
    filename TEXT NOT NULL,
    applied_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS sources (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL CHECK(length(trim(name)) > 0),
    base_url TEXT NOT NULL UNIQUE,
    allowed_host TEXT NOT NULL UNIQUE,
    is_enabled INTEGER NOT NULL DEFAULT 1 CHECK(is_enabled IN (0,1)),
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS categories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_id INTEGER NOT NULL REFERENCES sources(id) ON DELETE RESTRICT,
    name TEXT NOT NULL COLLATE NOCASE CHECK(length(trim(name)) > 0),
    first_seen_at TEXT NOT NULL,
    UNIQUE(source_id,name),
    UNIQUE(id,source_id)
);

CREATE TABLE IF NOT EXISTS crawl_jobs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_id INTEGER NOT NULL DEFAULT 1 REFERENCES sources(id) ON DELETE RESTRICT,
    max_pages INTEGER NOT NULL CHECK(max_pages BETWEEN 1 AND 3),
    status TEXT NOT NULL DEFAULT 'PENDING'
        CHECK(status IN ('PENDING','RUNNING','COMPLETED','FAILED')),
    catalogue_pages_done INTEGER NOT NULL DEFAULT 0 CHECK(catalogue_pages_done >= 0),
    books_found INTEGER NOT NULL DEFAULT 0 CHECK(books_found >= 0),
    items_saved INTEGER NOT NULL DEFAULT 0 CHECK(items_saved >= 0),
    new_books INTEGER NOT NULL DEFAULT 0 CHECK(new_books >= 0),
    existing_books INTEGER NOT NULL DEFAULT 0 CHECK(existing_books >= 0),
    error_count INTEGER NOT NULL DEFAULT 0 CHECK(error_count >= 0),
    last_error TEXT,
    created_at TEXT NOT NULL,
    started_at TEXT,
    finished_at TEXT,
    CHECK(items_saved = new_books + existing_books),
    CHECK(catalogue_pages_done <= max_pages),
    CHECK(status NOT IN ('COMPLETED','FAILED') OR finished_at IS NOT NULL)
);

CREATE TABLE IF NOT EXISTS books (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_id INTEGER NOT NULL DEFAULT 1 REFERENCES sources(id) ON DELETE RESTRICT,
    category_id INTEGER NOT NULL,
    source_url TEXT NOT NULL UNIQUE,
    title TEXT NOT NULL CHECK(length(trim(title)) > 0),
    price_pence INTEGER NOT NULL CHECK(price_pence BETWEEN 0 AND 999999),
    rating INTEGER NOT NULL CHECK(rating BETWEEN 1 AND 5),
    availability TEXT NOT NULL CHECK(length(trim(availability)) > 0),
    image_url TEXT,
    upc TEXT,
    first_seen_at TEXT NOT NULL,
    last_seen_at TEXT NOT NULL,
    last_crawl_job_id INTEGER REFERENCES crawl_jobs(id) ON DELETE SET NULL,
    FOREIGN KEY(category_id,source_id) REFERENCES categories(id,source_id) ON DELETE RESTRICT
);

CREATE TABLE IF NOT EXISTS crawl_pages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    job_id INTEGER NOT NULL REFERENCES crawl_jobs(id) ON DELETE CASCADE,
    page_number INTEGER NOT NULL CHECK(page_number >= 1),
    page_url TEXT NOT NULL,
    books_discovered INTEGER NOT NULL DEFAULT 0 CHECK(books_discovered >= 0),
    visited_at TEXT NOT NULL,
    UNIQUE(job_id,page_number),
    UNIQUE(job_id,page_url)
);

CREATE TABLE IF NOT EXISTS crawl_job_books (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    job_id INTEGER NOT NULL REFERENCES crawl_jobs(id) ON DELETE CASCADE,
    book_id INTEGER NOT NULL REFERENCES books(id) ON DELETE RESTRICT,
    action TEXT NOT NULL CHECK(action IN ('NEW','UPDATED','UNCHANGED')),
    observed_price_pence INTEGER NOT NULL CHECK(observed_price_pence >= 0),
    observed_rating INTEGER NOT NULL CHECK(observed_rating BETWEEN 1 AND 5),
    observed_at TEXT NOT NULL,
    UNIQUE(job_id,book_id)
);

CREATE TABLE IF NOT EXISTS book_price_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    book_id INTEGER NOT NULL REFERENCES books(id) ON DELETE CASCADE,
    job_id INTEGER NOT NULL REFERENCES crawl_jobs(id) ON DELETE RESTRICT,
    old_price_pence INTEGER NOT NULL CHECK(old_price_pence >= 0),
    new_price_pence INTEGER NOT NULL CHECK(new_price_pence >= 0),
    changed_at TEXT NOT NULL,
    CHECK(old_price_pence != new_price_pence),
    UNIQUE(book_id,job_id)
);

CREATE TABLE IF NOT EXISTS crawl_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    job_id INTEGER NOT NULL REFERENCES crawl_jobs(id) ON DELETE CASCADE,
    level TEXT NOT NULL CHECK(level IN ('INFO','WARNING','ERROR')),
    event_type TEXT NOT NULL CHECK(length(trim(event_type)) > 0),
    message TEXT NOT NULL,
    created_at TEXT NOT NULL
);
