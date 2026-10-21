-- 002_indexes.sql | Query performance and single-active-job enforcement.
CREATE UNIQUE INDEX IF NOT EXISTS ux_jobs_one_active ON crawl_jobs((1))
    WHERE status IN ('PENDING','RUNNING');
CREATE INDEX IF NOT EXISTS idx_jobs_created ON crawl_jobs(id DESC);
CREATE INDEX IF NOT EXISTS idx_books_title ON books(title COLLATE NOCASE);
CREATE INDEX IF NOT EXISTS idx_books_price ON books(price_pence);
CREATE INDEX IF NOT EXISTS idx_books_category ON books(category_id);
CREATE INDEX IF NOT EXISTS idx_books_source ON books(source_id);
CREATE INDEX IF NOT EXISTS idx_pages_job ON crawl_pages(job_id,page_number);
CREATE INDEX IF NOT EXISTS idx_job_books_job ON crawl_job_books(job_id,action);
CREATE INDEX IF NOT EXISTS idx_price_changes_book ON book_price_history(book_id,changed_at DESC);
CREATE INDEX IF NOT EXISTS idx_events_job ON crawl_events(job_id,id DESC);
