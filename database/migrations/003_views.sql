-- 003_views.sql | Read-only reporting surfaces, not copies of live data.
CREATE VIEW IF NOT EXISTS v_books_detail AS
SELECT b.id,b.source_url,b.title,b.price_pence,
       ROUND(b.price_pence/100.0,2) AS price_gbp,
       b.rating,c.name AS category,b.availability,b.image_url,b.upc,
       s.name AS source_name,b.first_seen_at,b.last_seen_at,b.last_crawl_job_id
FROM books b
JOIN categories c ON c.id=b.category_id
JOIN sources s ON s.id=b.source_id;

CREATE VIEW IF NOT EXISTS v_category_summary AS
SELECT c.id,c.name AS category,COUNT(b.id) AS total_books,
       ROUND(AVG(b.price_pence)/100.0,2) AS average_price_gbp,
       ROUND(AVG(b.rating),2) AS average_rating
FROM categories c LEFT JOIN books b ON b.category_id=c.id
GROUP BY c.id,c.name;

CREATE VIEW IF NOT EXISTS v_job_overview AS
SELECT j.id,j.status,j.max_pages,j.catalogue_pages_done,j.books_found,
       j.items_saved,j.new_books,j.existing_books,j.error_count,
       j.created_at,j.started_at,j.finished_at,
       (SELECT COUNT(*) FROM crawl_job_books jb WHERE jb.job_id=j.id AND jb.action='UPDATED') AS updated_books,
       (SELECT COUNT(*) FROM crawl_job_books jb WHERE jb.job_id=j.id AND jb.action='UNCHANGED') AS unchanged_books
FROM crawl_jobs j;
