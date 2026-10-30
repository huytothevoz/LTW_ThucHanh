PRAGMA foreign_keys=OFF;
BEGIN IMMEDIATE;

ALTER TABLE users ADD COLUMN role TEXT NOT NULL DEFAULT 'user'
    CHECK(role IN ('user','admin'));

DROP VIEW IF EXISTS v_books_detail;
DROP VIEW IF EXISTS v_category_summary;
DROP VIEW IF EXISTS v_job_overview;

DROP INDEX IF EXISTS ux_jobs_one_active;
DROP INDEX IF EXISTS idx_books_title;
DROP INDEX IF EXISTS idx_books_price;
DROP INDEX IF EXISTS idx_books_category;
DROP INDEX IF EXISTS idx_books_source;
DROP INDEX IF EXISTS idx_job_books_job;
DROP INDEX IF EXISTS idx_price_changes_book;
DROP INDEX IF EXISTS idx_bookmarks_user;
DROP INDEX IF EXISTS idx_price_notifications_user_unread;

ALTER TABLE books RENAME TO books_v5;
ALTER TABLE crawl_job_books RENAME TO crawl_job_books_v5;
ALTER TABLE book_price_history RENAME TO book_price_history_v5;
ALTER TABLE bookmarks RENAME TO bookmarks_v5;
ALTER TABLE price_change_notifications RENAME TO price_change_notifications_v5;

CREATE TABLE books (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_id INTEGER NOT NULL DEFAULT 1 REFERENCES sources(id) ON DELETE RESTRICT,
    category_id INTEGER NOT NULL,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    source_url TEXT NOT NULL,
    title TEXT NOT NULL CHECK(length(trim(title)) > 0),
    price_pence INTEGER NOT NULL CHECK(price_pence BETWEEN 0 AND 999999),
    rating INTEGER NOT NULL CHECK(rating BETWEEN 1 AND 5),
    availability TEXT NOT NULL CHECK(length(trim(availability)) > 0),
    image_url TEXT,
    upc TEXT,
    first_seen_at TEXT NOT NULL,
    last_seen_at TEXT NOT NULL,
    last_crawl_job_id INTEGER REFERENCES crawl_jobs(id) ON DELETE SET NULL,
    FOREIGN KEY(category_id,source_id) REFERENCES categories(id,source_id) ON DELETE RESTRICT,
    UNIQUE(user_id,source_url)
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

CREATE TABLE bookmarks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    book_id INTEGER NOT NULL REFERENCES books(id) ON DELETE CASCADE,
    note TEXT NOT NULL DEFAULT '' CHECK(length(note) <= 500),
    created_at TEXT NOT NULL,
    UNIQUE(user_id,book_id)
);

CREATE TABLE price_change_notifications (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    book_id INTEGER NOT NULL REFERENCES books(id) ON DELETE CASCADE,
    price_history_id INTEGER NOT NULL REFERENCES book_price_history(id) ON DELETE CASCADE,
    created_at TEXT NOT NULL,
    read_at TEXT,
    UNIQUE(user_id,price_history_id)
);

INSERT INTO books(
    id,source_id,category_id,user_id,source_url,title,price_pence,rating,availability,
    image_url,upc,first_seen_at,last_seen_at,last_crawl_job_id
)
WITH owner_refs(book_id,user_id) AS (
    SELECT jb.book_id,j.user_id
    FROM crawl_job_books_v5 jb JOIN crawl_jobs j ON j.id=jb.job_id
    UNION
    SELECT book_id,user_id FROM bookmarks_v5
    UNION
    SELECT book_id,user_id FROM price_change_notifications_v5
    UNION
    SELECT b.id,NULL FROM books_v5 b
    WHERE NOT EXISTS (SELECT 1 FROM crawl_job_books_v5 jb WHERE jb.book_id=b.id)
      AND NOT EXISTS (SELECT 1 FROM bookmarks_v5 bm WHERE bm.book_id=b.id)
      AND NOT EXISTS (SELECT 1 FROM price_change_notifications_v5 n WHERE n.book_id=b.id)
),
ranked_owners AS (
    SELECT b.id AS old_id,b.source_id,b.category_id,o.user_id,b.source_url,b.title,b.price_pence,b.rating,
           b.availability,b.image_url,b.upc,b.first_seen_at,b.last_seen_at,
           (
               SELECT MAX(j2.id)
               FROM crawl_job_books_v5 jb2
               JOIN crawl_jobs j2 ON j2.id=jb2.job_id
               WHERE jb2.book_id=b.id AND j2.user_id IS o.user_id
           ) AS last_crawl_job_id,
           ROW_NUMBER() OVER (
               PARTITION BY b.id
               ORDER BY (o.user_id IS last_job.user_id) DESC,o.user_id
           ) AS owner_rank
    FROM books_v5 b
    JOIN owner_refs o ON o.book_id=b.id
    LEFT JOIN crawl_jobs last_job ON last_job.id=b.last_crawl_job_id
)
SELECT CASE WHEN owner_rank=1 THEN old_id ELSE NULL END,source_id,category_id,user_id,source_url,
       title,price_pence,rating,availability,image_url,upc,first_seen_at,last_seen_at,last_crawl_job_id
FROM ranked_owners
ORDER BY CASE WHEN owner_rank=1 THEN 0 ELSE 1 END,old_id,owner_rank;

INSERT INTO crawl_job_books(id,job_id,book_id,action,observed_price_pence,observed_rating,observed_at)
SELECT jb.id,jb.job_id,b.id,jb.action,jb.observed_price_pence,jb.observed_rating,jb.observed_at
FROM crawl_job_books_v5 jb
JOIN crawl_jobs j ON j.id=jb.job_id
JOIN books_v5 old_book ON old_book.id=jb.book_id
JOIN books b ON b.source_url=old_book.source_url AND b.user_id IS j.user_id;
INSERT INTO book_price_history(id,book_id,job_id,old_price_pence,new_price_pence,changed_at)
SELECT h.id,b.id,h.job_id,h.old_price_pence,h.new_price_pence,h.changed_at
FROM book_price_history_v5 h
JOIN crawl_jobs j ON j.id=h.job_id
JOIN books_v5 old_book ON old_book.id=h.book_id
JOIN books b ON b.source_url=old_book.source_url AND b.user_id IS j.user_id;
INSERT INTO bookmarks(id,user_id,book_id,note,created_at)
SELECT bm.id,bm.user_id,b.id,bm.note,bm.created_at
FROM bookmarks_v5 bm
JOIN books_v5 old_book ON old_book.id=bm.book_id
JOIN books b ON b.source_url=old_book.source_url AND b.user_id IS bm.user_id;
INSERT INTO price_change_notifications(id,user_id,book_id,price_history_id,created_at,read_at)
SELECT n.id,n.user_id,b.id,h.id,n.created_at,n.read_at
FROM price_change_notifications_v5 n
JOIN book_price_history_v5 old_history ON old_history.id=n.price_history_id
JOIN crawl_jobs j ON j.id=old_history.job_id AND j.user_id IS n.user_id
JOIN books_v5 old_book ON old_book.id=n.book_id
JOIN books b ON b.source_url=old_book.source_url AND b.user_id IS n.user_id
JOIN book_price_history h ON h.id=old_history.id;

DROP TABLE price_change_notifications_v5;
DROP TABLE bookmarks_v5;
DROP TABLE book_price_history_v5;
DROP TABLE crawl_job_books_v5;
DROP TABLE books_v5;

CREATE INDEX idx_books_title ON books(title COLLATE NOCASE);
CREATE INDEX idx_books_price ON books(price_pence);
CREATE INDEX idx_books_category ON books(category_id);
CREATE INDEX idx_books_source ON books(source_id);
CREATE INDEX idx_books_user ON books(user_id,id DESC);
CREATE INDEX idx_job_books_job ON crawl_job_books(job_id,action);
CREATE INDEX idx_price_changes_book ON book_price_history(book_id,changed_at DESC);
CREATE INDEX idx_bookmarks_user ON bookmarks(user_id,created_at DESC);
CREATE INDEX idx_price_notifications_user_unread
    ON price_change_notifications(user_id,read_at,id DESC);
CREATE UNIQUE INDEX ux_jobs_one_active_per_user ON crawl_jobs(COALESCE(user_id,0))
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

INSERT INTO schema_migrations(version,filename,applied_at)
VALUES(6,'006_user_isolation_and_admin.sql','__APPLIED_AT__');

PRAGMA user_version=6;
COMMIT;
PRAGMA foreign_keys=ON;
