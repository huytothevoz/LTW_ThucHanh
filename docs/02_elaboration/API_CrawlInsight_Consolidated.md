# CRAWLINSIGHT — API SPECIFICATION (CONSOLIDATED)

**Dự án:** `LTW-TH` · **Học phần:** 503073 — Lập trình Web & Ứng dụng · **Đề tài:** 07 — Web Crawling  
**Phiên bản tài liệu:** API 4.2 — Consolidated · **Ngày:** 21/10/2026  
**Pha RUP:** `02_elaboration` · **Trạng thái:** Baseline hợp đồng API theo source V4, chờ nhóm review & xác minh E2E.  
**Tài liệu liên quan:** `SRS_CrawlInsight_Consolidated.md` (SRS 4.2), `../03_construction/IMPLEMENTATION_STATUS_Consolidated.md`.

> **Nguồn hợp nhất:** `docs/API.md` (hợp đồng V2), `docs/API_V4.md` (V4), và backend hiện tại trong `routes/web.php`, `app/Http/Controllers/`, `app/Services/`, Laravel middleware cùng crawler/database Python. Tài liệu này **thay thế cả API V2 lẫn API_V4**, không nối hai danh sách endpoint mâu thuẫn nhau. Đường dẫn và trạng thái bên dưới mô tả **code hiện có**, không chứng minh đã nghiệm thu HTTP thực tế trên Windows.

## 1. Mục đích và phạm vi

API cung cấp dữ liệu giữa frontend Twig + JavaScript và Laravel/PHP, gồm: xác thực, hồ sơ, cài đặt cá nhân, tạo/giám sát crawl job, duyệt sách, lưu sách, lịch sử, thống kê và xuất CSV. Python/Scrapy chỉ chạy worker crawler và ghi SQLite qua `src.db` cùng `src/database/`; **không có một crawler REST service riêng**.

- **Base URL local:** `http://127.0.0.1:8000`; tất cả JSON API có tiền tố `/api`.
- **Phiên bản URL:** baseline **không dùng** `/api/v1` hay `/api/crawl-jobs`; không tự ý đổi endpoint nếu chưa cập nhật frontend, test và SRS.
- **Website crawl:** chỉ `https://books.toscrape.com/`, 1–3 trang catalogue/job, mỗi thời điểm tối đa một job toàn hệ thống.
- **Phạm vi ứng dụng:** Laravel/PHP chạy local cùng SQLite; Python chỉ phục vụ crawler. Không serve source hoặc SQLite trực tiếp bằng Apache.
- **Mục tiêu tài liệu:** để người làm frontend, backend, crawler hiểu giống nhau về tên field, quyền truy cập, lỗi và ví dụ payload.

## 2. Quy ước giao tiếp và bảo mật

| Quy tắc | Hợp đồng hiện hành |
|---|---|
| Dữ liệu JSON | `Content-Type: application/json` khi gửi body; trường API theo `snake_case`. |
| Phiên | Cookie session cùng origin. JavaScript nên dùng `credentials: "same-origin"` khi cần. |
| Xác thực | Trừ các API công khai được đánh dấu, endpoint yêu cầu tài khoản đang đăng nhập; guest nhận HTTP `401`. |
| CSRF | **Tất cả** request `POST`, `PUT`, `PATCH`, `DELETE` cần `X-CSRF-Token` lấy từ `<meta name="csrf-token">` của trang cùng session; sai/thiếu → `403 INVALID_CSRF`, kể cả route auth công khai. |
| Login/logout | Token CSRF phiên thay đổi khi session được làm mới; client phải lấy token mới trước mutation tiếp theo. |
| Mã lỗi | `{"error":{"code":"MACHINE_CODE","message":"Thông báo cho người dùng"}}`. HTTP status quyết định thành công/thất bại. |
| Không lộ bí mật | Không trả password hash, SMTP secret hoặc reset token trừ `local_test_link` có điều kiện trong chế độ kiểm thử local. |
| Thời gian | Các trường mốc thời gian của database dùng chuỗi UTC dạng ISO `YYYY-MM-DDTHH:MM:SSZ`. |
| Giá sách | Lưu `price_pence` integer GBP × 100; bộ lọc `min_price`/`max_price` truyền theo chuỗi GBP thập phân. |
| Dữ liệu multi-user | `books/categories/sources` dùng chung; `bookmarks/saved_searches/crawl_jobs` của người dùng chỉ thấy qua quyền sở hữu. |

### 2.1. Ví dụ gọi API có CSRF

```javascript
const csrf = document.querySelector('meta[name="csrf-token"]')?.content;
const res = await fetch('/api/jobs', {
  method: 'POST',
  credentials: 'same-origin',
  headers: { 'Content-Type': 'application/json', 'X-CSRF-Token': csrf },
  body: JSON.stringify({ max_pages: 2 }),
});
const data = await res.json();
if (!res.ok) throw new Error(data.error?.message || 'Request failed');
```

**Lưu ý:** sau register/login/logout/reset, nếu tiếp tục gọi API mutation mà không reload trang, cần cập nhật token từ một trang/token hợp lệ của phiên mới; không được reuse token trước login. `api_error` trả lỗi JSON; không được coi một thông báo thành công của frontend là bằng chứng DB đã thay đổi.

## 3. Bảng tổng hợp endpoint chính thức

**Public** = không yêu cầu login, nhưng mutation vẫn phải có CSRF. **Owner** = yêu cầu login và kiểm tra đúng chủ dữ liệu.

| Nhóm | Method | URL | Quyền | Mục đích |
|---|---|---|---|---|
| Health | GET | `/api/health` | Public | Trạng thái ứng dụng local |
| Auth | GET | `/api/auth/me` | Public | User hiện tại hoặc `null`, preferences |
| Auth | POST | `/api/auth/register` | Public + CSRF | Đăng ký và tạo session |
| Auth | POST | `/api/auth/login` | Public + CSRF | Đăng nhập |
| Auth | POST | `/api/auth/logout` | Login + CSRF | Đăng xuất |
| Auth | POST | `/api/auth/request-reset` | Public + CSRF | Gửi hướng dẫn khôi phục nếu SMTP sẵn sàng |
| Auth | POST | `/api/auth/reset-password` | Public + CSRF | Đặt lại mật khẩu bằng token |
| Profile | PATCH | `/api/me/profile` | Login + CSRF | Sửa họ tên |
| Profile | PATCH | `/api/me/preferences` | Login + CSRF | Sửa VI/EN, theme, book layout |
| Profile | POST | `/api/me/password` | Login + CSRF | Đổi mật khẩu, yêu cầu đăng nhập lại |
| Crawl | GET | `/api/summary` | Login | Tổng quan kho sách + job cá nhân |
| Crawl | POST | `/api/jobs` | Login + CSRF | Tạo crawl job, khởi động worker |
| Crawl | GET | `/api/jobs/{id}` | Owner | Theo dõi job và tối đa 30 event |
| Crawl | GET | `/api/history` | Login | Danh sách tối đa 100 job của user |
| Books | GET | `/api/books` | Login | Tìm kiếm/lọc/phân trang sách |
| Books | GET | `/api/books/{id}` | Login | Chi tiết sách + lịch sử giá |
| Books | GET | `/api/bookmarks` | Login | Sách đã lưu của user |
| Books | POST | `/api/bookmarks/{id}` | Login + CSRF | Lưu sách |
| Books | DELETE | `/api/bookmarks/{id}` | Login + CSRF | Bỏ lưu sách |
| Searches | GET | `/api/saved-searches` | Login | Xem bộ lọc đã lưu |
| Searches | POST | `/api/saved-searches` | Login + CSRF | Lưu bộ lọc |
| Searches | DELETE | `/api/saved-searches/{id}` | Owner + CSRF | Xóa bộ lọc |
| Analytics | GET | `/api/analytics` | Login | Thống kê danh mục/giá/đánh giá |
| Sources | GET | `/api/sources` | Login | Nguồn được duyệt |
| Export | GET | `/api/exports/books.csv` | Login | CSV UTF-8 BOM, dữ liệu sách chung |

**HTML routes không phải JSON API:** `/` landing; `/login`, `/register`, `/forgot-password`, `/reset-password/<token>` công khai; `/workspace`, `/books`, `/saved`, `/history`, `/analytics`, `/sources`, `/settings`, `/help` yêu cầu login. Hai đường `/books` (HTML) và `/api/books` (JSON) là hai endpoint khác nhau.

## 4. Authentication & account contracts

### 4.1. GET `/api/auth/me`

- **200:** `{"user": null, "preferences": null}` nếu khách; nếu đã đăng nhập: `user` chứa `id`, `full_name`, `email`, `created_at`, `last_login_at`, `is_active`; `preferences` có `locale`, `theme`, `book_layout`.
- **Không được** trả `password_hash`, `session_version`, reset token.

### 4.2. POST `/api/auth/register`

```json
{"full_name":"Nguyễn Văn A","email":"a@example.com","password":"Example12345"}
```

- **201:** `{"user": {"id":1,"full_name":"Nguyễn Văn A","email":"a@example.com", "created_at":"...", "last_login_at":null, "is_active":1},"preferences":{"locale":"vi","theme":"system","book_layout":"grid"}}`.
- **400 `VALIDATION_ERROR`:** tên 2–100 ký tự, email hợp lệ/không trùng, password 10–128 ký tự có chữ và số.
- **403 `INVALID_CSRF`:** thiếu token bảo vệ request.
- **Side effect:** tạo `users` + `user_preferences`, đăng nhập luôn và làm mới session.

### 4.3. POST `/api/auth/login`

```json
{"email":"a@example.com","password":"Example12345"}
```

- **200:** `{"user":{...},"preferences":{...}}` và session mới.
- **401 `INVALID_CREDENTIALS`:** sai email hoặc mật khẩu; không chỉ ra phần nào sai.
- **429 `TOO_MANY_ATTEMPTS`:** bị giới hạn sau số lần thất bại theo chính sách hiện có.

### 4.4. POST `/api/auth/logout`

- Body `{}` hoặc không có JSON body; **200** `{"ok":true}`; session cũ bị xóa.
- User chưa đăng nhập: **401 `AUTH_REQUIRED`**; thiếu CSRF: **403 `INVALID_CSRF`**.

### 4.5. POST `/api/auth/request-reset`

```json
{"email":"a@example.com"}
```

- **200:** `{"message":"Nếu email đã tồn tại, bạn sẽ nhận được hướng dẫn khôi phục."}`; không tiết lộ email tồn tại hay không.
- Nếu có user và SMTP được cấu hình: gửi email chứa link reset (chưa xác nhận email thật trong môi trường bàn giao).
- Khi `TESTING=true` hoặc `ALLOW_LOCAL_RESET_LINKS=1` **và** request xuất phát từ localhost, có thể trả thêm `local_test_link` cho thử nghiệm; **không phải chế độ production**.
- **503 `MAIL_NOT_CONFIGURED`** nếu SMTP không sẵn sàng và không bật local opt-in; **503 `EMAIL_DELIVERY_FAILED`** khi có lỗi gửi email đã được bắt; **429** khi quá ngưỡng.
- Token khôi phục: 20 phút, một lần dùng, hash trong DB; yêu cầu thực nghiệm ở TC-07/08.

### 4.6. POST `/api/auth/reset-password`

```json
{"token":"TOKEN_FROM_EMAIL_OR_LOCAL_TEST","password":"NewSecure12345"}
```

- **200:** `{"ok":true}`; xóa session đang dùng và tăng `session_version` để vô hiệu hóa phiên cũ.
- **400 `INVALID_TOKEN`** token sai/đã dùng/hết hạn; **400 `VALIDATION_ERROR`** password không hợp lệ.

### 4.7. Hồ sơ & tùy chọn

| API | Body ví dụ | Response 200 | Kiểm tra |
|---|---|---|---|
| `PATCH /api/me/profile` | `{"full_name":"Phạm Ngọc Duy"}` | `{"user":{...}}` | 2–100 ký tự |
| `PATCH /api/me/preferences` | `{"locale":"en","theme":"dark","book_layout":"list"}` | `{"preferences":{"locale":"en","theme":"dark","book_layout":"list"}}` | Chỉ key/giá trị cho phép; update từng phần được |
| `POST /api/me/password` | `{"current_password":"Old12345678","new_password":"New12345678"}` | `{"ok":true,"reauth_required":true}` | Mật khẩu hiện tại đúng; logout bắt buộc |

`locale` ∈ `{vi,en}`, `theme` ∈ `{light,dark,system}`, `book_layout` ∈ `{grid,list}`. `PATCH` body rỗng hoặc key lạ trả **400 `VALIDATION_ERROR`**. Dữ liệu sửa được ghi vào user hiện tại, không dùng ID user do client truyền.

## 5. Crawl job & monitoring contracts

### 5.1. POST `/api/jobs`

```json
{"max_pages":2}
```

- Body **chỉ có đúng một key** `max_pages`; giá trị là **JSON integer** 1, 2 hoặc 3. Bị từ chối: `"2"`, `true`, `2.0`, 0, 4, field `url`, key thừa, body không phải object.
- **202 Accepted:**

```json
{"job":{"id":14,"status":"PENDING","max_pages":2,"created_at":"2026-10-21T09:00:00Z"}}
```

- **400 `INVALID_MAX_PAGES`** nếu body không hợp lệ; **409 `JOB_ALREADY_ACTIVE`** nếu có job PENDING/RUNNING toàn hệ thống; **503 `CRAWLER_LAUNCH_FAILED`** nếu không khởi động được subprocess.
- Job mới được liên kết với `user_id` của session. Worker được chạy qua `python -m crawler.run_job --job-id N`; không cho phép URL do client chọn.

### 5.2. GET `/api/jobs/{id}`

```json
{
  "job": {
    "id":14,"status":"RUNNING","max_pages":2,
    "catalogue_pages_done":1,"books_found":20,"items_saved":15,
    "new_books":15,"existing_books":0,"error_count":0,
    "last_error":null,"created_at":"2026-10-21T09:00:00Z",
    "started_at":"2026-10-21T09:00:02Z","finished_at":null
  },
  "events":[{"id":5,"job_id":14,"level":"INFO","event_type":"STARTED","message":"Crawler process started","created_at":"..."}]
}
```

Response minh họa lược bớt trường: đối tượng `job` thực tế là bản ghi `crawl_jobs` gồm cả `source_id` và `user_id`; không tự ý giả định object chỉ chứa các trường như ví dụ. Dữ liệu `events` là tối đa 30 bản ghi mới nhất, theo `id DESC`.

- Trạng thái: `PENDING` → `RUNNING` → `COMPLETED` hoặc `FAILED` (job có thể từ PENDING → FAILED khi không launch được).
- **404 `JOB_NOT_FOUND`** nếu job không tồn tại **hoặc thuộc user khác**; không tiết lộ quyền sở hữu.
- Client có thể polling 2 giây/lần khi chưa terminal; refresh không tạo thêm job.

### 5.3. GET `/api/summary` và GET `/api/history`

`GET /api/summary` → **200** ví dụ với database rỗng:

```json
{
  "total_books":0,"completed_jobs":0,"saved_books":0,
  "last_job":null,"recent_jobs":[],
  "rating_distribution":[
    {"rating":1,"count":0},{"rating":2,"count":0},
    {"rating":3,"count":0},{"rating":4,"count":0},{"rating":5,"count":0}
  ]
}
```

`total_books`/`rating_distribution` phản ánh kho sách **dùng chung**. `completed_jobs`, `last_job`, `recent_jobs` (tối đa 5), `saved_books` là dữ liệu của tài khoản hiện tại. `GET /api/history` → `{"items":[...]}` chứa tối đa 100 job của user, sắp xếp mới nhất trước.

## 6. Books, bookmark & searches contracts

### 6.1. GET `/api/books`

| Query | Giá trị cho phép | Mặc định |
|---|---|---|
| `q` | Chuỗi tìm tên ≤100 ký tự; SQL LIKE an toàn, tìm không phân biệt hoa/thường | `""` |
| `min_price` | Chuỗi số tiền GBP hợp lệ, tối đa 2 số sau dấu chấm | không đặt |
| `max_price` | Như trên; nếu có cả hai cần min ≤ max | không đặt |
| `page` | Số nguyên dương, hỗ trợ tới 100000 | `1` |

**200:**

```json
{
  "items":[{
    "id":12,"title":"Example Book (illustrative)","price_pence":1299,
    "rating":4,"category":"Travel","availability":"In stock",
    "image_url":null,"source_url":"https://books.toscrape.com/catalogue/example_1/index.html"
  }],
  "page":1,"page_size":12,"total":1,"total_pages":1,
  "bookmarked_ids":[12]
}
```

**Quan trọng:** Dữ liệu JSON trên chỉ là **minh họa hợp đồng**, không phải dữ liệu thực ở DB. Nếu DB rỗng, `items=[]`, `total=0`, `total_pages=0`, `bookmarked_ids=[]`. Phân trang 12 sách/trang; trang vượt giới hạn trả danh sách rỗng nếu `page` hợp lệ. **400 `INVALID_FILTER`** cho query sai.

### 6.2. GET `/api/books/{id}`

- **200:** `{"book":{...},"is_bookmarked":false,"price_history":[{"old_price_pence":1500,"new_price_pence":1299,"changed_at":"..."}]}`.
- `book` là bản ghi từ `v_books_detail`, có thể chứa các cột bổ sung (ví dụ category, source name); `price_history` tối đa 30 bản ghi, mới trước.
- **404 `BOOK_NOT_FOUND`** nếu sách không tồn tại.

### 6.3. Bookmarks của tài khoản

| API | Kết quả | Lỗi |
|---|---|---|
| `GET /api/bookmarks?page=1` | `{"items":[...],"total":0,"page":1,"page_size":12,"total_pages":0}` | 400 `INVALID_PAGE` |
| `POST /api/bookmarks/{id}` | `{"book_id":12,"saved":true}`; gọi lại không tạo trùng | 404 `BOOK_NOT_FOUND` |
| `DELETE /api/bookmarks/{id}` | `{"book_id":12,"saved":false}`; xóa lặp vẫn hợp lệ | thiếu CSRF → 403 |

### 6.4. Saved searches của tài khoản

```json
{"name":"Sách dưới £20","q":"travel","min_price":"0","max_price":"20"}
```

- `POST /api/saved-searches` → **201** `{"item":{"id":7,"name":"Sách dưới £20"}}`; tên từ 1–60 ký tự, `q` ≤100; tối đa 20 bộ lọc/tài khoản, GBP min ≤ max.
- `GET /api/saved-searches` → **200** `{"items":[{"id":7,"name":"Sách dưới £20","query":"travel","min_price":"0","max_price":"20","created_at":"..."}]}`.
- **Lưu ý hợp đồng:** API tạo nhận trường **`q`**, nhưng bản ghi trả về trường **`query`** (theo schema); frontend phải map chính xác, tránh lỗi sau refactor.
- `DELETE /api/saved-searches/{id}` → **200** `{"ok":true}` nếu owner, **404 `NOT_FOUND`** nếu ID không có hoặc không thuộc chủ sở hữu.

## 7. Analytics, approved sources, CSV

### 7.1. GET `/api/analytics`

**200:**

```json
{
  "categories":[{"category":"Travel","total_books":5,"average_price_gbp":24.90}],
  "prices":{"minimum":500,"maximum":5000,"average":1800,"total":5},
  "rating_distribution":[{"rating":1,"count":0},{"rating":2,"count":1}]
}
```

`prices.minimum/maximum/average` lấy từ `books.price_pence` (đơn vị **pence**, dù tên nhãn hiển thị trên UI phải là GBP). Category view `average_price_gbp` có đơn vị GBP. Các giá trị chỉ mang tính minh họa; khi không có sách, min/max/average có thể là `null` và `total=0`. `rating_distribution` thực tế có đủ 5 mức 1..5.

### 7.2. GET `/api/sources`

**200** `{"items":[{"id":1,"name":"Books to Scrape","base_url":"https://books.toscrape.com/","allowed_host":"books.toscrape.com","is_enabled":1,"created_at":"..."}]}`. Không có API thêm/xóa/chỉnh sửa nguồn trong baseline.

### 7.3. GET `/api/exports/books.csv`

- **200**, `text/csv; charset=utf-8`, `Content-Disposition: attachment; filename="crawlinsight-books.csv"`.
- Có BOM UTF-8 để mở Excel; tiêu đề `id,title,price_gbp,rating,category,availability,source_url`.
- Kết quả là **kho sách dùng chung**, không phải chỉ sách đã lưu; stream theo record, giá chuyển pence/100 thành GBP 2 chữ số.
- Text cells beginning with formula-significant characters are prefixed to reduce CSV formula injection risk; validate this behavior with Excel/LibreOffice before closing TC-28.

## 8. Mã lỗi và nguyên tắc frontend

| HTTP | `error.code` | Khi nào thường xảy ra | Hướng xử lý UI |
|---|---|---|---|
| 400 | `INVALID_MAX_PAGES`, `INVALID_FILTER`, `INVALID_PAGE`, `VALIDATION_ERROR`, `INVALID_TOKEN` | Input sai/token lỗi | Hiển thị lỗi cạnh input; giữ giá trị form |
| 401 | `AUTH_REQUIRED`, `INVALID_CREDENTIALS` | Chưa đăng nhập/sai mật khẩu | Dẫn login hoặc hiển thị lỗi |
| 403 | `INVALID_CSRF` | CSRF cũ/thiếu | Reload form/token; không retry tự động mutation |
| 404 | `NOT_FOUND`, `BOOK_NOT_FOUND`, `JOB_NOT_FOUND` | Không tồn tại hoặc không phải owner | Hiển thị trạng thái không tìm thấy |
| 409 | `JOB_ALREADY_ACTIVE` | Có crawl job khác đang chạy | Theo dõi job hiện hữu, không tạo lặp |
| 429 | `TOO_MANY_ATTEMPTS` | Rate limit login/reset | Chờ hết thời hạn hạn chế |
| 503 | `MAIL_NOT_CONFIGURED`, `EMAIL_DELIVERY_FAILED`, `CRAWLER_LAUNCH_FAILED` | Dịch vụ phụ trợ lỗi | Nêu lý do; không báo thành công giả |
| 500 | `INTERNAL_ERROR` | Lỗi server chưa xử lý | Ghi log nội bộ, thông báo chung |

Frontend luôn kiểm tra `response.ok`, không chỉ parse JSON. Không hiển thị giá pence như GBP; không tự lập dữ liệu rỗng giả khi API lỗi; đối với 404 của job/book owner khác không suy luận thành vấn đề mạng.

## 9. Mapping FR → route → module → test

| Nhóm FR trong SRS 4.2 | API/route tương ứng | Source owner | TC cần nghiệm thu |
|---|---|---|---|
| FR-PUB-01..04 | `/`, `/login`, `/register` | `routes/web.php`, `PageController`, `templates/` | TC-02 |
| FR-AUT-01..10 | `/api/auth/*`, `/api/me/*` | `ApiController`, `AccountService`, identity middleware | TC-03..09 |
| FR-USR-01..05 | `/api/me/preferences`, `/settings`, `/books` | `AccountService`, `common.js`, Twig templates | TC-10..13 |
| FR-CRW-01..12 | `/api/jobs`, `/api/jobs/{id}`, `/api/summary` | `ApiController`, `CrawlJobService`, `crawler/*` | TC-14..22 |
| FR-BOO-01..08 | `/api/books*`, `/api/bookmarks*`, `/api/saved-searches*`, CSV | `ApiController`, `BookService`, `AccountService` | TC-23..28 |
| FR-WSP-01..06 | `/api/summary`, `/api/history`, `/api/analytics`, `/api/sources` | `ApiController`, `templates/*` | TC-29..33 |
| FR-PLT-01..05 | CSRF middleware, health, migrations, setup | Laravel middleware, `database/*`, `scripts/*` | TC-01, TC-34..37 |

**Hợp đồng đóng băng tại V4.2:** nếu đổi field/status/route, hãy (1) tạo issue/change request, (2) sửa API Markdown này, (3) bổ sung unit/integration test, (4) cập nhật frontend, (5) cập nhật FR/TC trong SRS và Excel, (6) review trước merge. Không đổi API âm thầm bằng AI Agent.

## 10. Kiểm chứng còn thiếu trước khi gọi là ổn định

1. Cài PHP/Composer và Python/Scrapy trên Windows, chạy PHPUnit và crawler tests.
2. HTTP integration cho login→create job→detail→books→bookmark→logout, dùng cùng cookie jar và CSRF.
3. Test redirect/session khi đổi mật khẩu và khi reset password từ hai trình duyệt khác nhau.
4. Crawl thật 1–2 trang Books to Scrape, xem logs, DB, giá pence và trạng thái terminal.
5. Test email SMTP thật, trường hợp cấu hình thiếu, trường hợp gửi thất bại.
6. Test CSV trong Excel với Unicode **và** chuỗi bắt đầu `=`, `+`, `-`, `@` trước nghiệm thu bảo mật.
7. Đánh dấu kết quả và ảnh/log trong `IMPLEMENTATION_STATUS_Consolidated.md` + Excel; không đưa demo-generated fixtures vào DB runtime.

---

**Quy tắc tài liệu:** `API_CrawlInsight_Consolidated.md` là bản đặc tả duy nhất; `.docx` được xuất từ bản Markdown. Hai tài liệu `API.md` và `API_V4.md` cũ là tư liệu lịch sử và không còn dùng làm hợp đồng chính.
