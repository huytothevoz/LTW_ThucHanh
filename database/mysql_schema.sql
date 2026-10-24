CREATE TABLE IF NOT EXISTS schema_migrations (
    version INT NOT NULL PRIMARY KEY,
    filename VARCHAR(128) NOT NULL,
    applied_at VARCHAR(32) NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS sources (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    base_url VARCHAR(512) NOT NULL UNIQUE,
    allowed_host VARCHAR(255) NOT NULL UNIQUE,
    is_enabled TINYINT(1) NOT NULL DEFAULT 1,
    created_at VARCHAR(32) NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS users (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
    full_name VARCHAR(100) NOT NULL,
    email VARCHAR(254) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    role VARCHAR(16) NOT NULL DEFAULT 'user',
    is_active TINYINT(1) NOT NULL DEFAULT 1,
    session_version INT UNSIGNED NOT NULL DEFAULT 0,
    created_at VARCHAR(32) NOT NULL,
    updated_at VARCHAR(32) NOT NULL,
    last_login_at VARCHAR(32) NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS categories (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
    source_id BIGINT UNSIGNED NOT NULL,
    name VARCHAR(255) NOT NULL,
    first_seen_at VARCHAR(32) NOT NULL,
    UNIQUE KEY uq_categories_source_name (source_id, name),
    UNIQUE KEY uq_categories_id_source (id, source_id),
    CONSTRAINT fk_categories_source FOREIGN KEY (source_id) REFERENCES sources(id) ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS crawl_jobs (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
    source_id BIGINT UNSIGNED NOT NULL DEFAULT 1,
    max_pages TINYINT UNSIGNED NOT NULL,
    status VARCHAR(16) NOT NULL DEFAULT 'PENDING',
    catalogue_pages_done INT UNSIGNED NOT NULL DEFAULT 0,
    books_found INT UNSIGNED NOT NULL DEFAULT 0,
    items_saved INT UNSIGNED NOT NULL DEFAULT 0,
    new_books INT UNSIGNED NOT NULL DEFAULT 0,
    existing_books INT UNSIGNED NOT NULL DEFAULT 0,
    error_count INT UNSIGNED NOT NULL DEFAULT 0,
    last_error VARCHAR(1000) NULL,
    created_at VARCHAR(32) NOT NULL,
    started_at VARCHAR(32) NULL,
    finished_at VARCHAR(32) NULL,
    user_id BIGINT UNSIGNED NULL,
    active_user_key BIGINT GENERATED ALWAYS AS (
        CASE WHEN status IN ('PENDING', 'RUNNING') THEN COALESCE(user_id, 0) ELSE NULL END
    ) STORED,
    UNIQUE KEY ux_jobs_one_active_per_user (active_user_key),
    KEY idx_jobs_created (id DESC),
    KEY idx_crawl_jobs_user (user_id, id DESC),
    CONSTRAINT fk_crawl_jobs_source FOREIGN KEY (source_id) REFERENCES sources(id) ON DELETE RESTRICT,
    CONSTRAINT fk_crawl_jobs_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL,
    CHECK (max_pages BETWEEN 1 AND 3),
    CHECK (status IN ('PENDING', 'RUNNING', 'COMPLETED', 'FAILED')),
    CHECK (items_saved = new_books + existing_books),
    CHECK (catalogue_pages_done <= max_pages),
    CHECK (status NOT IN ('COMPLETED', 'FAILED') OR finished_at IS NOT NULL)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS books (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
    source_id BIGINT UNSIGNED NOT NULL DEFAULT 1,
    category_id BIGINT UNSIGNED NOT NULL,
    user_id BIGINT UNSIGNED NULL,
    source_url VARCHAR(2000) NOT NULL,
    source_url_hash CHAR(64) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
    title VARCHAR(500) NOT NULL,
    price_pence INT UNSIGNED NOT NULL,
    rating TINYINT UNSIGNED NOT NULL,
    availability VARCHAR(255) NOT NULL,
    image_url VARCHAR(1000) NULL,
    upc VARCHAR(255) NULL,
    first_seen_at VARCHAR(32) NOT NULL,
    last_seen_at VARCHAR(32) NOT NULL,
    last_crawl_job_id BIGINT UNSIGNED NULL,
    UNIQUE KEY uq_books_user_url (user_id, source_url_hash),
    KEY idx_books_title (title),
    KEY idx_books_price (price_pence),
    KEY idx_books_category (category_id),
    KEY idx_books_source (source_id),
    KEY idx_books_user (user_id, id DESC),
    CONSTRAINT fk_books_source FOREIGN KEY (source_id) REFERENCES sources(id) ON DELETE RESTRICT,
    CONSTRAINT fk_books_category_source FOREIGN KEY (category_id, source_id) REFERENCES categories(id, source_id) ON DELETE RESTRICT,
    CONSTRAINT fk_books_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    CONSTRAINT fk_books_last_job FOREIGN KEY (last_crawl_job_id) REFERENCES crawl_jobs(id) ON DELETE SET NULL,
    CHECK (price_pence <= 999999),
    CHECK (rating BETWEEN 1 AND 5)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS crawl_pages (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
    job_id BIGINT UNSIGNED NOT NULL,
    page_number INT UNSIGNED NOT NULL,
    page_url VARCHAR(2000) NOT NULL,
    books_discovered INT UNSIGNED NOT NULL DEFAULT 0,
    visited_at VARCHAR(32) NOT NULL,
    UNIQUE KEY uq_crawl_pages_job_page (job_id, page_number),
    UNIQUE KEY uq_crawl_pages_job_url (job_id, page_url(500)),
    KEY idx_pages_job (job_id, page_number),
    CONSTRAINT fk_crawl_pages_job FOREIGN KEY (job_id) REFERENCES crawl_jobs(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS crawl_job_books (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
    job_id BIGINT UNSIGNED NOT NULL,
    book_id BIGINT UNSIGNED NOT NULL,
    action VARCHAR(16) NOT NULL,
    observed_price_pence INT UNSIGNED NOT NULL,
    observed_rating TINYINT UNSIGNED NOT NULL,
    observed_at VARCHAR(32) NOT NULL,
    UNIQUE KEY uq_crawl_job_books_job_book (job_id, book_id),
    KEY idx_job_books_job (job_id, action),
    CONSTRAINT fk_crawl_job_books_job FOREIGN KEY (job_id) REFERENCES crawl_jobs(id) ON DELETE CASCADE,
    CONSTRAINT fk_crawl_job_books_book FOREIGN KEY (book_id) REFERENCES books(id) ON DELETE RESTRICT,
    CHECK (action IN ('NEW', 'UPDATED', 'UNCHANGED')),
    CHECK (observed_rating BETWEEN 1 AND 5)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS book_price_history (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
    book_id BIGINT UNSIGNED NOT NULL,
    job_id BIGINT UNSIGNED NOT NULL,
    old_price_pence INT UNSIGNED NOT NULL,
    new_price_pence INT UNSIGNED NOT NULL,
    changed_at VARCHAR(32) NOT NULL,
    UNIQUE KEY uq_price_history_book_job (book_id, job_id),
    KEY idx_price_changes_book (book_id, changed_at DESC),
    CONSTRAINT fk_price_history_book FOREIGN KEY (book_id) REFERENCES books(id) ON DELETE CASCADE,
    CONSTRAINT fk_price_history_job FOREIGN KEY (job_id) REFERENCES crawl_jobs(id) ON DELETE RESTRICT,
    CHECK (old_price_pence <> new_price_pence)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS crawl_events (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
    job_id BIGINT UNSIGNED NOT NULL,
    level VARCHAR(16) NOT NULL,
    event_type VARCHAR(64) NOT NULL,
    message TEXT NOT NULL,
    created_at VARCHAR(32) NOT NULL,
    KEY idx_events_job (job_id, id DESC),
    CONSTRAINT fk_crawl_events_job FOREIGN KEY (job_id) REFERENCES crawl_jobs(id) ON DELETE CASCADE,
    CHECK (level IN ('INFO', 'WARNING', 'ERROR'))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS user_preferences (
    user_id BIGINT UNSIGNED NOT NULL PRIMARY KEY,
    locale VARCHAR(8) NOT NULL DEFAULT 'vi',
    theme VARCHAR(16) NOT NULL DEFAULT 'system',
    book_layout VARCHAR(16) NOT NULL DEFAULT 'grid',
    updated_at VARCHAR(32) NOT NULL,
    CONSTRAINT fk_user_preferences_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    CHECK (locale IN ('vi', 'en')),
    CHECK (theme IN ('light', 'dark', 'system')),
    CHECK (book_layout IN ('grid', 'list'))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS bookmarks (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
    user_id BIGINT UNSIGNED NOT NULL,
    book_id BIGINT UNSIGNED NOT NULL,
    note VARCHAR(500) NOT NULL DEFAULT '',
    created_at VARCHAR(32) NOT NULL,
    UNIQUE KEY uq_bookmarks_user_book (user_id, book_id),
    KEY idx_bookmarks_user (user_id, created_at DESC),
    CONSTRAINT fk_bookmarks_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    CONSTRAINT fk_bookmarks_book FOREIGN KEY (book_id) REFERENCES books(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS saved_searches (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
    user_id BIGINT UNSIGNED NOT NULL,
    name VARCHAR(60) NOT NULL,
    query VARCHAR(100) NOT NULL DEFAULT '',
    min_price VARCHAR(12) NOT NULL DEFAULT '',
    max_price VARCHAR(12) NOT NULL DEFAULT '',
    created_at VARCHAR(32) NOT NULL,
    KEY idx_saved_searches_user (user_id, id DESC),
    CONSTRAINT fk_saved_searches_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS password_reset_tokens (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
    user_id BIGINT UNSIGNED NOT NULL,
    token_hash CHAR(64) NOT NULL UNIQUE,
    expires_at VARCHAR(32) NOT NULL,
    used_at VARCHAR(32) NULL,
    created_at VARCHAR(32) NOT NULL,
    KEY idx_reset_user_expiry (user_id, expires_at),
    CONSTRAINT fk_password_reset_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS auth_attempts (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
    subject_hash CHAR(64) NOT NULL,
    attempted_at VARCHAR(32) NOT NULL,
    success TINYINT(1) NOT NULL,
    KEY idx_attempts_subject_time (subject_hash, attempted_at),
    CHECK (success IN (0, 1))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS price_change_notifications (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
    user_id BIGINT UNSIGNED NOT NULL,
    book_id BIGINT UNSIGNED NOT NULL,
    price_history_id BIGINT UNSIGNED NOT NULL,
    created_at VARCHAR(32) NOT NULL,
    read_at VARCHAR(32) NULL,
    UNIQUE KEY uq_price_notifications_user_history (user_id, price_history_id),
    KEY idx_price_notifications_user_unread (user_id, read_at, id DESC),
    CONSTRAINT fk_price_notifications_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    CONSTRAINT fk_price_notifications_book FOREIGN KEY (book_id) REFERENCES books(id) ON DELETE CASCADE,
    CONSTRAINT fk_price_notifications_history FOREIGN KEY (price_history_id) REFERENCES book_price_history(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS legacy_imports (
    source_path VARCHAR(700) NOT NULL PRIMARY KEY,
    imported_at VARCHAR(32) NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE OR REPLACE VIEW v_books_detail AS
SELECT b.id,b.source_url,b.title,b.price_pence,
       ROUND(b.price_pence/100.0,2) AS price_gbp,
       b.rating,c.name AS category,b.availability,b.image_url,b.upc,
       s.name AS source_name,b.first_seen_at,b.last_seen_at,b.last_crawl_job_id
FROM books b
JOIN categories c ON c.id=b.category_id
JOIN sources s ON s.id=b.source_id;

CREATE OR REPLACE VIEW v_category_summary AS
SELECT c.id,c.name AS category,COUNT(b.id) AS total_books,
       ROUND(AVG(b.price_pence)/100.0,2) AS average_price_gbp,
       ROUND(AVG(b.rating),2) AS average_rating
FROM categories c LEFT JOIN books b ON b.category_id=c.id
GROUP BY c.id,c.name;

CREATE OR REPLACE VIEW v_job_overview AS
SELECT j.id,j.status,j.max_pages,j.catalogue_pages_done,j.books_found,
       j.items_saved,j.new_books,j.existing_books,j.error_count,
       j.created_at,j.started_at,j.finished_at,
       (SELECT COUNT(*) FROM crawl_job_books jb WHERE jb.job_id=j.id AND jb.action='UPDATED') AS updated_books,
       (SELECT COUNT(*) FROM crawl_job_books jb WHERE jb.job_id=j.id AND jb.action='UNCHANGED') AS unchanged_books
FROM crawl_jobs j;
