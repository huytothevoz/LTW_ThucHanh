-- CrawlInsight v5 | Reference SQL for a FRESH EMPTY install.

-- Runtime migrations 001..005 remain authoritative for existing users.

-- Includes one trusted source; NO books and NO user accounts.

PRAGMA foreign_keys=ON;

BEGIN IMMEDIATE;

CREATE TABLE auth_attempts (
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 subject_hash TEXT NOT NULL,
 attempted_at TEXT NOT NULL,
 success INTEGER NOT NULL CHECK(success IN (0,1))
);

CREATE TABLE book_price_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    book_id INTEGER NOT NULL REFERENCES books(id) ON DELETE CASCADE,
    job_id INTEGER NOT NULL REFERENCES crawl_jobs(id) ON DELETE RESTRICT,
    old_price_pence INTEGER NOT NULL CHECK(old_price_pence >= 0),
    new_price_pence INTEGER NOT NULL CHECK(new_price_pence >= 0),
    changed_at TEXT NOT NULL,
    CHECK(old_price_pence != new_price_pence),
    UNIQUE(book_id,job_id)
);

CREATE TABLE price_change_notifications (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    book_id INTEGER NOT NULL REFERENCES books(id) ON DELETE CASCADE,
    price_history_id INTEGER NOT NULL REFERENCES book_price_history(id) ON DELETE CASCADE,
    created_at TEXT NOT NULL,
    read_at TEXT,
    UNIQUE(user_id, price_history_id)
);

CREATE TABLE bookmarks (
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
 book_id INTEGER NOT NULL REFERENCES books(id) ON DELETE CASCADE,
 note TEXT NOT NULL DEFAULT '' CHECK(length(note) <= 500),
 created_at TEXT NOT NULL,
 UNIQUE(user_id,book_id)
);

CREATE TABLE books (
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

CREATE TABLE categories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_id INTEGER NOT NULL REFERENCES sources(id) ON DELETE RESTRICT,
    name TEXT NOT NULL COLLATE NOCASE CHECK(length(trim(name)) > 0),
    first_seen_at TEXT NOT NULL,
    UNIQUE(source_id,name),
    UNIQUE(id,source_id)
);

CREATE TABLE crawl_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    job_id INTEGER NOT NULL REFERENCES crawl_jobs(id) ON DELETE CASCADE,
    level TEXT NOT NULL CHECK(level IN ('INFO','WARNING','ERROR')),
    event_type TEXT NOT NULL CHECK(length(trim(event_type)) > 0),
    message TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE crawl_job_books (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    job_id INTEGER NOT NULL REFERENCES crawl_jobs(id) ON DELETE CASCADE,
    book_id INTEGER NOT NULL REFERENCES books(id) ON DELETE RESTRICT,
    action TEXT NOT NULL CHECK(action IN ('NEW','UPDATED','UNCHANGED')),
    observed_price_pence INTEGER NOT NULL CHECK(observed_price_pence >= 0),
    observed_rating INTEGER NOT NULL CHECK(observed_rating BETWEEN 1 AND 5),
    observed_at TEXT NOT NULL,
    UNIQUE(job_id,book_id)
);

CREATE TABLE crawl_jobs (
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
    finished_at TEXT, user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
    CHECK(items_saved = new_books + existing_books),
    CHECK(catalogue_pages_done <= max_pages),
    CHECK(status NOT IN ('COMPLETED','FAILED') OR finished_at IS NOT NULL)
);

CREATE TABLE crawl_pages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    job_id INTEGER NOT NULL REFERENCES crawl_jobs(id) ON DELETE CASCADE,
    page_number INTEGER NOT NULL CHECK(page_number >= 1),
    page_url TEXT NOT NULL,
    books_discovered INTEGER NOT NULL DEFAULT 0 CHECK(books_discovered >= 0),
    visited_at TEXT NOT NULL,
    UNIQUE(job_id,page_number),
    UNIQUE(job_id,page_url)
);

CREATE TABLE password_reset_tokens (
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
 token_hash TEXT NOT NULL UNIQUE,
 expires_at TEXT NOT NULL,
 used_at TEXT,
 created_at TEXT NOT NULL
);

CREATE TABLE saved_searches (
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
 name TEXT NOT NULL CHECK(length(trim(name)) BETWEEN 1 AND 60),
 query TEXT NOT NULL DEFAULT '' CHECK(length(query)<=100),
 min_price TEXT NOT NULL DEFAULT '' CHECK(length(min_price)<=12),
 max_price TEXT NOT NULL DEFAULT '' CHECK(length(max_price)<=12),
 created_at TEXT NOT NULL
);

CREATE TABLE schema_migrations (
    version INTEGER PRIMARY KEY CHECK(version >= 1),
    filename TEXT NOT NULL,
    applied_at TEXT NOT NULL
);

CREATE TABLE sources (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL CHECK(length(trim(name)) > 0),
    base_url TEXT NOT NULL UNIQUE,
    allowed_host TEXT NOT NULL UNIQUE,
    is_enabled INTEGER NOT NULL DEFAULT 1 CHECK(is_enabled IN (0,1)),
    created_at TEXT NOT NULL
);

CREATE TABLE user_preferences (
 user_id INTEGER PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
 locale TEXT NOT NULL DEFAULT 'vi' CHECK(locale IN ('vi','en')),
 theme TEXT NOT NULL DEFAULT 'system' CHECK(theme IN ('light','dark','system')),
 book_layout TEXT NOT NULL DEFAULT 'grid' CHECK(book_layout IN ('grid','list')),
 updated_at TEXT NOT NULL
);

CREATE TABLE users (
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

CREATE INDEX idx_attempts_subject_time ON auth_attempts(subject_hash,attempted_at);

CREATE INDEX idx_bookmarks_user ON bookmarks(user_id,created_at DESC);

CREATE INDEX idx_books_category ON books(category_id);

CREATE INDEX idx_books_price ON books(price_pence);

CREATE INDEX idx_books_source ON books(source_id);

CREATE INDEX idx_books_title ON books(title COLLATE NOCASE);

CREATE INDEX idx_crawl_jobs_user ON crawl_jobs(user_id,id DESC);

CREATE INDEX idx_events_job ON crawl_events(job_id,id DESC);

CREATE INDEX idx_job_books_job ON crawl_job_books(job_id,action);

CREATE INDEX idx_jobs_created ON crawl_jobs(id DESC);

CREATE INDEX idx_pages_job ON crawl_pages(job_id,page_number);

CREATE INDEX idx_price_changes_book ON book_price_history(book_id,changed_at DESC);

CREATE INDEX idx_price_notifications_user_unread
    ON price_change_notifications(user_id,read_at,id DESC);

CREATE INDEX idx_reset_user_expiry ON password_reset_tokens(user_id,expires_at);

CREATE INDEX idx_saved_searches_user ON saved_searches(user_id,id DESC);

CREATE UNIQUE INDEX ux_jobs_one_active ON crawl_jobs((1))
    WHERE status IN ('PENDING','RUNNING');

CREATE VIEW v_books_detail AS
SELECT b.id,b.source_url,b.title,b.price_pence,
       ROUND(b.price_pence/100.0,2) AS price_gbp,
       b.rating,c.name AS category,b.availability,b.image_url,b.upc,
       s.name AS source_name,b.first_seen_at,b.last_seen_at,b.last_crawl_job_id
FROM books b
JOIN categories c ON c.id=b.category_id
JOIN sources s ON s.id=b.source_id;

CREATE VIEW v_category_summary AS
SELECT c.id,c.name AS category,COUNT(b.id) AS total_books,
       ROUND(AVG(b.price_pence)/100.0,2) AS average_price_gbp,
       ROUND(AVG(b.rating),2) AS average_rating
FROM categories c LEFT JOIN books b ON b.category_id=c.id
GROUP BY c.id,c.name;

CREATE VIEW v_job_overview AS
SELECT j.id,j.status,j.max_pages,j.catalogue_pages_done,j.books_found,
       j.items_saved,j.new_books,j.existing_books,j.error_count,
       j.created_at,j.started_at,j.finished_at,
       (SELECT COUNT(*) FROM crawl_job_books jb WHERE jb.job_id=j.id AND jb.action='UPDATED') AS updated_books,
       (SELECT COUNT(*) FROM crawl_job_books jb WHERE jb.job_id=j.id AND jb.action='UNCHANGED') AS unchanged_books
FROM crawl_jobs j;

INSERT INTO sources(id,name,base_url,allowed_host,is_enabled,created_at) VALUES(1,'Books to Scrape','https://books.toscrape.com/','books.toscrape.com',1,'2026-10-21T00:00:00Z');

INSERT INTO schema_migrations(version,filename,applied_at) VALUES(1,'001_core.sql','2026-10-21T00:00:00Z');

INSERT INTO schema_migrations(version,filename,applied_at) VALUES(2,'002_indexes.sql','2026-10-21T00:00:00Z');

INSERT INTO schema_migrations(version,filename,applied_at) VALUES(3,'003_views.sql','2026-10-21T00:00:00Z');

INSERT INTO schema_migrations(version,filename,applied_at) VALUES(4,'004_identity_and_workspace.sql','2026-10-21T00:00:00Z');

INSERT INTO schema_migrations(version,filename,applied_at) VALUES(5,'005_price_change_notifications.sql','2026-10-23T00:00:00Z');

COMMIT;

PRAGMA user_version=5;
