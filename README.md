# CrawlInsight — Book Crawling & Analytics

> **Web Programming & Applications (503073) · Midterm Topic 7 — Web Crawling**  
> **Status:** Source baseline implemented; live crawling has not yet been verified on this authoring machine because external network and Flask/Scrapy packages are unavailable here. Team must run the live acceptance test on its Windows machine.

CrawlInsight là ứng dụng demo học thuật thu thập **dữ liệu sách thật từ [Books to Scrape](https://books.toscrape.com/)**, lưu vào SQLite rồi cho phép người dùng theo dõi job, tìm kiếm sách, lọc theo giá và xem biểu đồ đánh giá. Không có user account; chỉ dành cho **localhost**.

## 1. Đúng phạm vi SRS 2.0

- **Hai trang:** `/` Overview + Crawl Monitor và `/books` Book Explorer.
- **Nguồn cố định:** `https://books.toscrape.com/`; **1–3 trang danh sách** mỗi lần crawl, mặc định 1.
- **Crawler:** Python Scrapy theo link Next và trang chi tiết, tuân thủ robots.txt, giới hạn 1 request concurrent và 1 giây delay.
- **Dữ liệu:** tên, giá GBP (lưu pence), mức sao, danh mục, tình trạng tồn kho, ảnh/UPC nếu có.
- **Database:** đúng 2 bảng `books` và `crawl_jobs`; chỉ có 1 job đang hoạt động; upsert chống trùng.
- **Không có:** login, crawling website tùy ý, CSV export, WebSockets, worker daemon, admin dashboard nhiều nguồn.

**Chưa nên tuyên bố đã đạt 100%** khi chưa chạy live smoke test. Chi tiết kiểm chứng: `docs/IMPLEMENTATION_STATUS.md`.

Chi tiết toàn bộ folder/file có trong [`PROJECT_STRUCTURE.md`](PROJECT_STRUCTURE.md).

## 2. Cây thư mục

```text
CrawlInsight/
├── START_HERE.bat                 # Windows quick start (safe)
├── app.py                         # Flask routes & subprocess launcher
├── requirements.txt, .env.example, .gitignore
├── SRS_CrawlInsight_10Days.md      # Đặc tả khóa phạm vi
├── database/schema.sql             # SQLite, 2 tables
├── src/db.py                       # SQLite transactions / analytics / filters
├── crawler/
│   ├── parser.py                   # HTML extractors / pure parser helpers
│   ├── settings.py                 # robots.txt, delay, concurrency
│   ├── pipelines.py                # transactional item upsert
│   ├── run_job.py                  # child-process job runner
│   └── spiders/books_spider.py     # catalogue -> Next -> detail
├── templates/                      # Jinja HTML pages, icons
├── static/css/style.css            # responsive visual design
├── static/js/                     # API clients, polling, search
├── static/img/                    # local brand assets (not book data)
├── data/                           # DB/log files generated locally (gitignored)
├── scripts/                        # Windows setup, start, tests
├── tests/                          # offline fixtures & pytest
└── docs/                           # API, architecture, coding rules, handoff notes
```

## 3. Cài trên Windows 10 / 11

**Yêu cầu:** Python **3.11 hoặc 3.12** có `venv` và `pip`; Internet để cài packages và crawl; Chrome/Edge. Không cần XAMPP, PHP hay MySQL. Port mặc định `5000`. Không cần domain và không cần cấu hình mail.

### Cách A: Dùng file BAT

Giải nén ZIP, mở thư mục `CrawlInsight` rồi chạy **`START_HERE.bat`**. Script chỉ tạo `.venv` **bên trong thư mục này**, cài packages, **tạo DB nếu chưa có** rồi chạy Flask. Nó không xóa bất cứ thư mục/DB nào và không động đến `htdocs`.

> Nếu Windows có cảnh báo thực thi, đọc và xem script trước khi chạy. Không chạy file nguồn tải từ nơi không tin cậy.

### Cách B: PowerShell thủ công (ưu tiên khi debug)

```powershell
cd CrawlInsight
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -c "from src.db import init_db; init_db()"
.\.venv\Scripts\python.exe app.py
```

Nếu không có Python 3.12, dùng `py -3.11`. Không bắt buộc `Activate.ps1`; dùng interpreter trực tiếp tránh lỗi Execution Policy. Truy cập **http://127.0.0.1:5000/**.

Nếu port 5000 bị chiếm:

```powershell
$env:FLASK_PORT = '5055'
.\.venv\Scripts\python.exe app.py
```

Sau đó mở `http://127.0.0.1:5055/`. Web chỉ bind `127.0.0.1`, không mở ra Internet/LAN.

## 4. Test ngay sau khi setup

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

**Đừng dùng test fixture HTML để tạo dữ liệu sách trên web.** Database production bắt đầu trống. Fixture trong `tests/fixtures` chỉ dùng cho kiểm thử selector và parsing.

### Chạy acceptance test bằng dữ liệu nguồn thật

1. Mở `/`, xác nhận **Total books = 0** sau khi setup trên DB mới.
2. Chọn **1 page** → `Start crawling`; theo dõi chuyển `PENDING → RUNNING → COMPLETED` (hoặc xem lỗi). Crawl chậm vì giới hạn request.
3. Đợi hoàn tất, mở `/books`; kiểm tra card sách lấy từ SQLite, search và filter giá `min_price=10`, `max_price=40`.
4. Quay về Dashboard, kiểm tra biểu đồ đánh giá có số liệu, và lịch sử job mới nhất.
5. Chạy lại **1 page**; kiểm tra `total_books` không tăng do trùng URL và `existing_books` > 0.
6. Chạy **2 pages**, chứng minh spider đi theo link Next, không chỉ lấy catalogue trang đầu. Khi nguồn ổn định và có dữ liệu, số `catalogue_pages_done` mong đợi là 2.
7. Mở một lần crawl, thử nhấn Start trong lúc chạy hoặc gọi POST lần 2: **HTTP 409** và không tạo worker thứ hai.
8. Dùng Chrome DevTools → Network xem `/api/summary`, `/api/jobs/<id>`, `/api/books`, và kiểm tra không có dữ liệu mock.

Nếu nguồn không truy cập được, UI phải hiển thị FAILED/last_error. **Đừng chuyển sang dữ liệu giả rồi quay video như dữ liệu live.** Tests parser dùng fixture offline để chứng minh extraction logic.

## 5. Các JSON endpoint

| Route | Method | Chức năng |
|---|---|---|
| `/api/summary` | GET | Tổng sách, rating 1–5, last job và 5 lần chạy gần đây |
| `/api/jobs` | POST | Tạo job với JSON `{"max_pages": 1}` (202 hoặc 400/409/503) |
| `/api/jobs/<id>` | GET | Trạng thái job cùng counters |
| `/api/books` | GET | Danh sách + `q`, `min_price`, `max_price`, `page`; 12 item/trang |

Chi tiết body và quy tắc lỗi xem `docs/API.md` hoặc mục 8 của SRS.

## 6. Cách dữ liệu di chuyển

```text
Browser → POST /api/jobs → Flask creates PENDING job in SQLite
                         ↳ subprocess: python -m crawler.run_job --job-id N
                               ↓
                          RUNNING / Scrapy
                               ↓
       HTTPS catalogue → next page + book detail (robots, limit, retry)
                               ↓
        parser.py → SQLiteBookPipeline → atomic upsert + counters
                               ↓
            COMPLETED / FAILED in crawl_jobs
                               ↓
Browser polls GET /api/jobs/N every 2s, refreshes API summary/books
```

**Không có real-time WebSocket.** Giới hạn 1–3 pages áp dụng cho catalogue, **không** phải tổng số HTTP requests. Mỗi trang có thể dẫn tới nhiều request chi tiết.

## 7. Debug và khôi phục an toàn

- **`ModuleNotFoundError: flask/scrapy`:** dùng đúng `.venv\Scripts\python.exe`; cài lại requirements trong .venv, đừng cài tùy tiện vào Python toàn máy.
- **`Address already in use`:** đổi `FLASK_PORT`, không kill service khác.
- **Source không phản hồi / 403/robots policy:** kiểm tra Internet và file `data/logs/crawl-job-N.log`. Không tăng tốc, không bypass robots/chặn.
- **Job có error_count > 0 nhưng vẫn COMPLETED:** có item lưu được, song vẫn có lỗi nhỏ; UI ghi “Completed with warnings”.
- **Job stuck RUNNING khi máy hoặc process bị kill:** đây là giới hạn MVP. Chỉ khi **đã xác nhận** không còn process `crawler.run_job` chạy thì backup `data/crawlinsight.db`, chạy công cụ sửa trạng thái thủ công:

```powershell
.\.venv\Scripts\python.exe -m src.recover_job --job-id 1 --confirm
```

Lệnh chỉ đánh FAILED cho **job đang PENDING/RUNNING** theo ID được chọn, **không xóa sách**. Tuyệt đối không chạy trên job vẫn đang xử lý.
- **Muốn tạo DB trống để demo:** đổi tên DB cũ và file WAL/SHM khi đã dừng toàn bộ process (không xóa vĩnh viễn); sau đó chạy `init_db()`. Tránh thao tác khi process còn hoạt động.

## 8. Team coding baseline

- Code identifiers viết tiếng Anh, tuân thủ PEP 8 cho Python; JS camelCase; CSS class kebab-case; DB và API fields đúng **snake_case trong SRS 2.0**.
- Không commit `.venv`, `.env`, `data/*.db`, `data/logs/`.
- PR nhỏ, một chủ đề, review trước merge `main`. Không force-push `main` dùng chung.
- Không thay contract SRS mà không chỉnh tests + code consumers cùng lúc.
- **Mỗi thành viên sẽ được phân công chính thức sau**; xem `docs/IMPLEMENTATION_STATUS.md` để biết điểm cần xác minh/bổ sung.

## 9. Các điều kiện hạn chế và sử dụng có trách nhiệm

- Chỉ crawler trên sandbox công khai được thiết kế cho scraping. Link bên ngoài host đều bị từ chối trong spider.
- `ROBOTSTXT_OBEY=True`; 1 concurrent request; download delay >= 1s; tối đa 1 retry; không cố vượt chặn.
- SQLite chỉ phù hợp single-machine teaching demo; **không deploy public** vì không có authentication.
- Mức giá và rating trên Books to Scrape là **dữ liệu giả lập của nguồn**, không phục vụ thương mại.
- Khi báo cáo/video, phân biệt rõ “đã code”, “đã test offline” và “đã xác minh live”.

**Nguồn:** `SRS_CrawlInsight_10Days.md`, tài liệu môn `503073-Midterm-V1.docx`, [Scrapy](https://docs.scrapy.org/en/latest/), [Flask](https://flask.palletsprojects.com/), [SQLite](https://www.sqlite.org/).
