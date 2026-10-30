# DATA DICTIONARY — CrawlInsight MySQL Database V6

Tài liệu này giải thích **dữ liệu lưu thực tế trong MySQL/MariaDB**. Tên cột là hợp đồng kỹ thuật; phần ví dụ chỉ nhằm giúp đọc DB, không phải dữ liệu crawl. Các migration SQLite cũ chỉ được giữ lại để nhập dữ liệu và chạy kiểm thử.

## Quy ước thống nhất

| Quy ước | Giá trị/ý nghĩa |
|---|---|
| `id` | BIGINT AUTO_INCREMENT, khóa chính; không dùng làm URL sách |
| `_id` | Khóa ngoại tới bảng tương ứng |
| `_at` | Thời điểm UTC dạng `YYYY-MM-DDTHH:MM:SSZ` (VARCHAR ISO-8601) |
| `price_pence` | Đơn vị **pence (GBP)**, số nguyên; `1234` = £12.34 |
| `source_url` | URL HTTPS sách nguồn đã kiểm tra domain, duy nhất trong từng tài khoản |
| `NULL` | Không trích xuất được hoặc dữ liệu tùy chọn, khác chuỗi rỗng |
| `rating` | Số nguyên 1–5, nguồn trang sản phẩm |
| `status` | `PENDING`, `RUNNING`, `COMPLETED`, `FAILED` |
| `action` | `NEW` = lần đầu gặp, `UPDATED` = trường lưu thay đổi, `UNCHANGED` = không đổi |

## 1. `sources` — nguồn crawl

| Cột | Kiểu | Bắt buộc | Mô tả |
|---|---|---|---|
| `id` | BIGINT PK | Có | Nguồn mặc định có ID = 1 |
| `name` | VARCHAR | Có | Tên hiển thị nguồn |
| `base_url` | VARCHAR UNIQUE | Có | Trang bắt đầu `https://books.toscrape.com/` |
| `allowed_host` | VARCHAR UNIQUE | Có | Tên miền whitelist `books.toscrape.com` |
| `is_enabled` | TINYINT CHECK(0/1) | Có | Cờ metadata; web MVP vẫn cố định source 1 |
| `created_at` | VARCHAR | Có | UTC lúc khởi tạo |

**Quan hệ:** một nguồn có nhiều danh mục, sách và job. Phiên bản hiện tại không cho phép thêm nguồn tự do từ UI vì spider chỉ hỗ trợ Books to Scrape; `is_enabled` chưa phải nút tắt crawler toàn hệ thống.

## 2. `categories` — danh mục

| Cột | Kiểu | Bắt buộc | Mô tả |
|---|---|---|---|
| `id` | BIGINT PK | Có | Mã danh mục |
| `source_id` | BIGINT FK → sources | Có | Danh mục thuộc nguồn nào |
| `name` | VARCHAR, case-insensitive collation | Có | Ví dụ `Travel`, `Science`; không trùng trong cùng nguồn |
| `first_seen_at` | VARCHAR | Có | Lần đầu crawler phát hiện danh mục |

**Quan hệ:** một category chứa nhiều books. Spider nhận text từ breadcrumb, code tự tạo category nếu chưa có. MySQL `utf8mb4_unicode_ci` so sánh tên không phân biệt hoa/thường.

## 3. `books` — dữ liệu sách MỚI NHẤT

| Cột | Kiểu | Bắt buộc | Mô tả |
|---|---|---|---|
| `id` | BIGINT PK | Có | Khóa nội bộ, giữ nguyên qua nhiều lượt crawl |
| `source_id` | BIGINT FK → sources | Có | Nguồn của sách |
| `category_id` | BIGINT FK → categories | Có | Khóa danh mục; cặp (category_id,source_id) phải hợp lệ |
| `user_id` | BIGINT FK → users | Không | Chủ sở hữu catalog; NULL chỉ dành cho dữ liệu legacy/chưa gán |
| `source_url` | VARCHAR(2000) | Có | URL chi tiết; URL hash unique trong phạm vi tài khoản |
| `source_url_hash` | CHAR(64) | Có | SHA-256 của URL; dùng làm khóa unique theo user để tránh giới hạn độ dài index MySQL |
| `title` | VARCHAR(500) | Có | Tên sách, đã chuẩn hóa khoảng trắng |
| `price_pence` | INTEGER 0..999999 | Có | Giá hiện tại, ví dụ `2599` là £25.99 |
| `rating` | INTEGER 1..5 | Có | Mức đánh giá sao |
| `availability` | TEXT | Có | Ví dụ `In stock` hoặc `Out of stock` |
| `image_url` | TEXT | Không | Link ảnh nguồn HTTPS, chỉ thuộc domain được duyệt |
| `upc` | TEXT | Không | Product code nếu nguồn có |
| `first_seen_at` | TEXT | Có | Ngày đầu tiên gặp URL này, không đổi khi recrawl |
| `last_seen_at` | TEXT | Có | Ngày gần nhất nhận lại sách thành công |
| `last_crawl_job_id` | INTEGER FK → crawl_jobs | Không | Job mới nhất đã cập nhật/nhìn thấy sách này |

**Lưu ý:** Không có cột `category` trực tiếp nữa vì tránh lặp dữ liệu; API `/api/books` vẫn trả `category` nhờ JOIN `categories`. Hãy dùng `v_books_detail` khi xem kết quả bằng SQL.

## 4. `crawl_jobs` — lần chạy crawler

| Cột | Kiểu | Bắt buộc | Mô tả |
|---|---|---|---|
| `id` | INTEGER PK | Có | Mã job; ví dụ `#5` |
| `source_id` | INTEGER FK → sources | Có | Nguồn cố định 1 |
| `max_pages` | INTEGER 1..3 | Có | Giới hạn **trang danh sách**, không phải số request |
| `status` | TEXT | Có | `PENDING` → `RUNNING` → `COMPLETED/FAILED` |
| `catalogue_pages_done` | INTEGER | Có | Số trang listing đã phân tích thành công |
| `books_found` | INTEGER | Có | Số URL chi tiết không trùng đã lên lịch từ catalogue |
| `items_saved` | INTEGER | Có | Số bản ghi quan sát lưu thành công, 1 sách tối đa 1 lần/job |
| `new_books` | INTEGER | Có | Số bản ghi sách chưa từng có trong DB |
| `existing_books` | INTEGER | Có | Số sách đã có trước job này, bao gồm updated/unchanged |
| `error_count` | INTEGER | Có | Số lỗi ghi nhận trong vòng đời job |
| `last_error` | TEXT | Không | Chuỗi lỗi cuối đã loại chi tiết nguy hiểm, tối đa 220 ký tự |
| `created_at` | TEXT | Có | Lúc API tạo job |
| `started_at` | TEXT | Không | Lúc worker bắt đầu |
| `finished_at` | TEXT | Không | Lúc kết thúc, bắt buộc nếu terminal |

**Quy tắc:** mỗi tài khoản chỉ có một job ở `PENDING/RUNNING` (được bảo vệ bằng generated unique key trong MySQL). `items_saved = new_books + existing_books`. Nếu crawler chết đột ngột có thể cần recovery thủ công (xem README chính).

## 5. `crawl_pages` — chứng cứ crawling qua trang listing

| Cột | Kiểu | Bắt buộc | Mô tả |
|---|---|---|---|
| `id` | INTEGER PK | Có | ID trang ghé |
| `job_id` | INTEGER FK | Có | Job sở hữu trang |
| `page_number` | INTEGER | Có | Thứ tự 1,2,3 |
| `page_url` | TEXT | Có | URL HTTPS của trang đã xử lý |
| `books_discovered` | INTEGER | Có | Số URL sách mới được scheduling từ trang đó |
| `visited_at` | TEXT | Có | Lúc parse trang thành công |

**UNIQUE:** `(job_id,page_number)` và index URL ngăn cùng một trang được đếm hai lần. Dòng này chứng minh spider có thực sự đi trang `page-2.html` hay không.

## 6. `crawl_job_books` — sách gặp trong từng lần crawl

| Cột | Kiểu | Bắt buộc | Mô tả |
|---|---|---|---|
| `id` | INTEGER PK | Có | Mã bản ghi quan sát |
| `job_id` | INTEGER FK | Có | Job hiện tại |
| `book_id` | INTEGER FK | Có | Sách được quan sát |
| `action` | TEXT ENUM | Có | `NEW`, `UPDATED`, `UNCHANGED` |
| `observed_price_pence` | INTEGER | Có | Giá thu được *tại lần crawl này* |
| `observed_rating` | INTEGER | Có | Rating thu được *tại lần crawl này* |
| `observed_at` | TEXT | Có | Thời điểm crawler lưu |

**UNIQUE:** `(job_id,book_id)`. Bảng này khác `books`: `books` là trạng thái hiện tại riêng của chủ sở hữu, `crawl_job_books` là lịch sử mỗi lần quan sát. Nếu sách đổi tiêu đề nhưng không đổi giá, `action=UPDATED` mà `book_price_history` không tăng.

## 7. `book_price_history` — thay đổi GIÁ thật giữa các job

| Cột | Kiểu | Bắt buộc | Mô tả |
|---|---|---|---|
| `id` | INTEGER PK | Có | ID biến động |
| `book_id` | INTEGER FK | Có | Sách thay giá |
| `job_id` | INTEGER FK | Có | Job phát hiện thay đổi |
| `old_price_pence` | INTEGER | Có | Giá trước update |
| `new_price_pence` | INTEGER | Có | Giá mới |
| `changed_at` | TEXT | Có | Thời điểm thay đổi |

**Đặc điểm:** không tạo dòng cho mỗi lần crawl nếu giá không đổi. Nếu về sau có chức năng price analytics, sử dụng bảng này, không suy luận từ timestamps.

## 8. `crawl_events` — sự kiện/nhật ký crawler

| Cột | Kiểu | Bắt buộc | Mô tả |
|---|---|---|---|
| `id` | INTEGER PK | Có | Mã log |
| `job_id` | INTEGER FK | Có | Job sinh log |
| `level` | TEXT ENUM | Có | `INFO`, `WARNING`, `ERROR` |
| `event_type` | TEXT | Có | `CREATED`, `STARTED`, `CRAWLER_ERROR`, `COMPLETED`, `FAILED` |
| `message` | TEXT | Có | Thông báo ngắn; lỗi được sanitize |
| `created_at` | TEXT | Có | UTC phát sinh sự kiện |

**Ứng dụng:** khi giảng viên hỏi job lỗi gì, có thể `SELECT * FROM crawl_events WHERE job_id = ? ORDER BY id DESC`. Không lưu full tracebacks hay HTML nguồn vào DB; traceback chi tiết nằm trong local log file (ngoài Apache web root trong XAMPP).

## 9. `schema_migrations` — các phiên bản lược đồ

| Cột | Kiểu | Bắt buộc | Mô tả |
|---|---|---|---|
| `version` | INTEGER PK | Có | Số thứ tự 1,2,3... |
| `filename` | TEXT | Có | Tên script áp dụng |
| `applied_at` | TEXT | Có | Thời điểm áp dụng |

Bảng này lưu metadata; không phải dữ liệu người dùng. Runtime MySQL khởi tạo từ `database/mysql_schema.sql`; lịch sử migration được quản lý bởi `src/database/migrations.py`. Không sửa tay số version.

## 10. View (không lưu thêm dòng dữ liệu)

| View | Các trường quan trọng | Dùng để làm gì |
|---|---|---|
| `v_books_detail` | `title`, `price_pence`, `price_gbp`, `rating`, `category`, `source_name` | Xem sách dạng bảng đã JOIN thông tin liên quan |
| `v_category_summary` | `category`, `total_books`, `average_price_gbp`, `average_rating` | Thống kê từng danh mục |
| `v_job_overview` | `id`, `status`, `new_books`, `existing_books`, `updated_books`, `unchanged_books` | Tìm hiểu kết quả của từng job |

## 11. Ví dụ cụ thể (mọi giá trị sau đây là minh họa)

Job #1 thấy `[DEMO] Understanding the Web` lần đầu → `books` thêm 1 dòng, `crawl_job_books` thêm 1 dòng `NEW`, `new_books +1`.

Job #2 thấy đúng URL đó với giá £25.99 chuyển thành £27.99 → `books.price_pence = 2799`, `crawl_job_books.action = UPDATED`, `book_price_history` có bản ghi `(2599→2799)`, `existing_books +1`.

Job #3 thấy giá không đổi và các field khác cũng không đổi → `crawl_job_books.action = UNCHANGED`, không thêm `book_price_history`, `existing_books +1`.

Những row của các ví dụ trên chỉ có trong **demo DB được ghi nhãn**, không tự động xuất hiện trong DB runtime.

---

## V4 addendum — users and personal workspace (2026-10-21)

The previous nine crawler tables remain unchanged except `crawl_jobs.user_id` (nullable FK to `users.id`). Data existing before V4 remains attached to no account (NULL) rather than being attributed to the next person who signs up.

| Table | Fields (high-level) | Meaning |
|---|---|---|
| `users` | `id`, `full_name`, `email` (unique case-insensitive), `password_hash`, `role` (`user`/`admin`), `is_active`, `session_version`, `created_at`, `updated_at`, `last_login_at` | Login identity and role; only `admin` can access `/admin/users`. |
| `user_preferences` | `user_id` (PK + FK), `locale` (vi/en), `theme` (light/dark/system), `book_layout` (grid/list), `updated_at` | One preference set per account. |
| `bookmarks` | `id`, `user_id`, `book_id`, `note`, `created_at`; `UNIQUE(user_id,book_id)` | Per-account saves; API allows saving only a book owned by the same account. |
| `saved_searches` | `id`, `user_id`, `name`, `query`, `min_price`, `max_price`, `created_at` | Personal search presets; max 20 per account, enforced in service logic. |
| `password_reset_tokens` | `id`, `user_id`, `token_hash`, `expires_at`, `used_at`, `created_at` | One-time 20-minute reset proof; stores SHA-256 of random token, **not** raw token. |
| `auth_attempts` | `id`, `subject_hash`, `attempted_at`, `success` | Login/reset request rate limiter; subject is hashed, not stored as raw IP/email. |
| `price_change_notifications` | `id`, `user_id`, `book_id`, `price_history_id`, `created_at`, `read_at` | One notification per bookmarked user and observed price-history row; unique `price_history_id` prevents duplicate alerts. |

## V5 addendum — per-user price change notifications

Migration `005_price_change_notifications.sql` adds in-app notifications when a crawler observes a price change for a book a user has bookmarked. The notification, price-history row and book update are committed in the same InnoDB transaction. Unchanged prices and books without bookmarks produce no notification. Notifications remain visible if the user later removes the bookmark; deleting the associated book or price-history row removes them.

The authenticated API returns the latest 20 notifications and the unread count. Users can mark one notification or all of their notifications as read; every query and update is scoped to the current account.

**Important:** The runtime MySQL database is *not* a demonstration data source. `database/mysql_schema.sql` is the runtime fresh-install schema; `database/schema.sql` and `database/migrations/` remain only for upgrading legacy SQLite input and isolated tests. Never publish reports from live user tables: they could reveal email addresses and password hashes.

## V6 addendum — private catalogs and administrator

Migration `006_user_isolation_and_admin.sql` adds `users.role`, adds nullable `books.user_id`, and makes book URLs unique per account. Existing shared books are copied to each prior owner found in crawl observations/bookmarks; the SQLite source is backed up before it is upgraded/imported. `sources` and category labels remain shared reference data; book records, prices, analytics, bookmarks, and exports are private to their owner. The admin screen is `/admin/users`; `ADMIN_EMAIL` in `.env` selects an existing verified account for administrator promotion.
