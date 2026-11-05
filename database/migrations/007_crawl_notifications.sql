CREATE TABLE IF NOT EXISTS crawl_notifications (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    job_id INTEGER NOT NULL UNIQUE REFERENCES crawl_jobs(id) ON DELETE CASCADE,
    status TEXT NOT NULL CHECK(status IN ('QUEUED','RUNNING','COMPLETED','FAILED')),
    created_at TEXT NOT NULL,
    read_at TEXT
);

CREATE INDEX IF NOT EXISTS idx_crawl_notifications_user_unread
    ON crawl_notifications(user_id,read_at,id DESC);

INSERT INTO schema_migrations(version,filename,applied_at)
VALUES(7,'007_crawl_notifications.sql','__APPLIED_AT__');

PRAGMA user_version=7;
