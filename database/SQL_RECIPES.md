# SQL RECIPES — kiểm tra CrawlInsight V3 bằng câu lệnh thật

Mọi truy vấn dưới đây đều dành cho **SQLite 3**, không phải MySQL. Có thể chạy trong DB Browser for SQLite → **Execute SQL**. Các câu `SELECT` không thay đổi dữ liệu. Không ghi SQL trực tiếp trong UI; Laravel API dùng service/query có parameter binding, còn crawler dùng `src/database` và parameterized queries.

## 1. Kiểm tra bảng, migration, dữ liệu

```sql
SELECT name, type FROM sqlite_master
WHERE type IN ('table','view') AND name NOT LIKE 'sqlite_%'
ORDER BY type,name;

SELECT * FROM schema_migrations ORDER BY version;
SELECT * FROM sources;
SELECT COUNT(*) AS total_books FROM books;
SELECT COUNT(*) AS total_jobs FROM crawl_jobs;
PRAGMA integrity_check;
PRAGMA foreign_key_check;
```

## 2. Danh sách sách rõ ràng kèm tên danh mục và giá GBP

```sql
SELECT id, title, category, price_pence, price_gbp, rating, availability,
       source_url, first_seen_at, last_seen_at
FROM v_books_detail ORDER BY id DESC LIMIT 20;
```

Tại sao dùng `v_books_detail`? Vì `books` có `category_id` chứ không lặp lại text `category`; view đã JOIN `books` + `categories` + `sources`.

## 3. Tìm sách theo tiêu đề và mức giá

```sql
-- Đơn vị lọc là pence; 1000 = £10, 3000 = £30.
SELECT title, category, price_gbp, rating
FROM v_books_detail
WHERE title LIKE '%python%' AND price_pence BETWEEN 1000 AND 3000
ORDER BY price_pence ASC;
```

Trong backend, giá trị người dùng được bind bằng placeholders `?`, không nối chuỗi SQL thủ công như ví dụ literal trên.

## 4. Phân bố rating, danh mục

```sql
SELECT rating, COUNT(*) AS total_books FROM books
GROUP BY rating ORDER BY rating;

SELECT * FROM v_category_summary
ORDER BY total_books DESC, category ASC;
```

## 5. Lịch sử crawler và kết quả mỗi lần

```sql
SELECT * FROM v_job_overview ORDER BY id DESC LIMIT 10;

SELECT job_id, page_number, page_url, books_discovered, visited_at
FROM crawl_pages WHERE job_id = 2 ORDER BY page_number;

SELECT jb.job_id, b.title, jb.action, jb.observed_price_pence,
       jb.observed_rating, jb.observed_at
FROM crawl_job_books jb JOIN books b ON b.id = jb.book_id
WHERE jb.job_id = 2 ORDER BY jb.id;
```

Từ kết quả `crawl_pages`, nhóm có thể chứng minh crawler đã theo `Next` hay chỉ dừng ở trang đầu.

## 6. Sách mới/cập nhật/không đổi

```sql
SELECT job_id,
       SUM(CASE WHEN action='NEW' THEN 1 ELSE 0 END) AS new_count,
       SUM(CASE WHEN action='UPDATED' THEN 1 ELSE 0 END) AS updated_count,
       SUM(CASE WHEN action='UNCHANGED' THEN 1 ELSE 0 END) AS unchanged_count
FROM crawl_job_books
GROUP BY job_id ORDER BY job_id DESC;
```

`new_count + updated_count + unchanged_count` phải bằng `items_saved` với các job v3 mới. Các job migrated từ v2 không có dữ liệu quan sát chi tiết lịch sử vì schema v2 chưa từng lưu; **không tạo dữ liệu lịch sử giả khi nâng cấp**.

## 7. Những cuốn thay đổi giá và lần thay đổi

```sql
SELECT b.title, h.old_price_pence / 100.0 AS old_gbp,
       h.new_price_pence / 100.0 AS new_gbp,
       (h.new_price_pence - h.old_price_pence) / 100.0 AS delta_gbp,
       h.job_id, h.changed_at
FROM book_price_history h JOIN books b ON b.id = h.book_id
ORDER BY h.changed_at DESC;
```

## 8. Xem sự kiện và lỗi từng job

```sql
SELECT job_id, level, event_type, message, created_at
FROM crawl_events WHERE job_id=2 ORDER BY id;

SELECT id, status, error_count, last_error, created_at, finished_at
FROM crawl_jobs WHERE error_count>0 ORDER BY id DESC;
```

## 9. SQL kiểm tra tính thống nhất giữa các bảng

```sql
-- Kết quả thông thường là 0 hàng (khi không có job v2 lịch sử).
SELECT j.id, j.items_saved, COUNT(jb.id) AS observed_rows
FROM crawl_jobs j LEFT JOIN crawl_job_books jb ON jb.job_id = j.id
WHERE j.id IN (SELECT DISTINCT job_id FROM crawl_job_books)
GROUP BY j.id HAVING j.items_saved != COUNT(jb.id);

-- Kết quả nên là 0 hàng: tổng counter sai invariant.
SELECT id FROM crawl_jobs WHERE items_saved != new_books + existing_books;

PRAGMA foreign_key_check;
PRAGMA integrity_check;
```

## 10. Import / export đúng cách

Không dùng phpMyAdmin để import `.sqlite3`; phpMyAdmin quản lý MySQL/MariaDB. Mở SQLite với DB Browser for SQLite hoặc lệnh:

```powershell
.\.venv\Scripts\python.exe -m database.tools.db_cli tables
.\.venv\Scripts\python.exe -m database.tools.db_cli rows v_books_detail --limit 20
.\.venv\Scripts\python.exe -m database.tools.db_cli export v_books_detail --format csv --output "$env:TEMP\ltw-books.csv"
```

Để làm database mới, dùng `python -m database.tools.db_cli init`, không chạy `DROP TABLE` hay `DELETE FROM` trên DB đang dùng.
