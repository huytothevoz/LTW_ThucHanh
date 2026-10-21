# CrawlInsight — Folder Structure & Ownership Guide

> Thuộc dự án SRS 2.0: đúng hai màn hình, hai bảng SQLite, một source Books to Scrape. Tất cả file dưới đây đã có trong gói source baseline, trừ dữ liệu SQLite/log chỉ sinh khi chạy.

```text
CrawlInsight/
├── START_HERE.bat                  # Cài dependencies rồi khởi chạy (Windows)
├── README.md                       # Setup, debug, live acceptance tests
├── PROJECT_STRUCTURE.md            # Cây thư mục + giải thích này
├── ideas.md                        # Ý tưởng A + một phần C, đã cập nhật 10 ngày
├── SRS_CrawlInsight_10Days.md      # Hợp đồng yêu cầu chính thức
├── requirements.txt                # Flask / Scrapy / pytest pinned
├── .env.example                    # Ví dụ cấu hình, không tự load
├── .editorconfig                   # Quy chuẩn indent/UTF-8
├── .gitignore                      # Chặn SQLite, log, cache, venv
├── app.py                          # HTTP pages, JSON APIs, job subprocess
├── src/
│   ├── __init__.py
│   ├── db.py                       # Schema init, transactions, books, jobs, stats
│   └── recover_job.py              # Thao tác MANUAL khôi phục job treo
├── database/
│   └── schema.sql                  # books + crawl_jobs, constraints & indexes
├── data/
│   └── .gitkeep                    # Local DB & job logs xuất hiện sau khi chạy
├── crawler/
│   ├── __init__.py
│   ├── run_job.py                  # Chạy Scrapy trong child process
│   ├── settings.py                 # robots, delays, concurrency, middleware
│   ├── middlewares.py              # Chặn HTTP/off-source kể cả redirect
│   ├── parser.py                   # Extract detail HTML, validate fields
│   ├── pipelines.py                # Atomic item upsert & job counters
│   └── spiders/
│       ├── __init__.py
│       └── books_spider.py         # Crawl catalogue -> Next -> detail
├── templates/
│   ├── _icons.html                 # SVG icon Jinja macro
│   ├── base.html                   # Layout, sidebar, navigation, toast
│   ├── dashboard.html              # KPIs, Start Crawl, Monitor, chart, history
│   ├── books.html                  # Search, price filter, books, pagination
│   ├── 404.html
│   └── 500.html
├── static/
│   ├── css/style.css               # Design system / mobile responsive
│   ├── js/common.js                # API fetch helper, toast, date, mobile nav
│   ├── js/dashboard.js             # Summary, start, poll 2s, chart, jobs
│   ├── js/books.js                 # Search/filter/pagination, safe book cards
│   └── img/favicon.svg            # Local brand icon
├── scripts/
│   ├── setup_windows.ps1          # Setup .venv and DB (no deletion)
│   ├── start_windows.ps1          # Flask local-only run
│   └── run_tests_windows.ps1       # Pytest command
├── tests/
│   ├── conftest.py                 # Separate temp DB per test
│   ├── fixtures/                   # Synthetic HTML only for tests
│   ├── test_db.py                  # SQLite/transaction/dedup/filter
│   ├── test_parser.py              # Price, rating, HTML detail extraction
│   ├── test_spider.py              # Catalogue link-following and max_pages
│   ├── test_api.py                 # Flask contract, invalid POST/409
│   └── test_settings.py            # Crawler safety
└── docs/
    ├── ARCHITECTURE.md             # Architecture/sequence diagrams
    ├── API.md                      # Request and response contract
    ├── CODING_CONVENTIONS.md       # Team rules and naming
    ├── IMPLEMENTATION_STATUS.md    # FR implementation + verification status
    ├── diagrams/.gitkeep           # Diagrams/evidence will be added by team
    ├── screenshots/.gitkeep        # Actual live screenshots, not mocks
    └── report/.gitkeep             # Midterm report work-in-progress
```

## Responsibility boundaries (chưa phân người)

- **Crawler subsystem:** `crawler/`, HTML fixtures, spider extraction tests.
- **Backend & DB subsystem:** `app.py`, `src/`, `database/`, worker integration and API tests.
- **Frontend subsystem:** `templates/`, `static/` and manual UI accessibility/responsiveness.
- **Documentation & integration:** `docs/`, SRS, README, setup scripts, end-to-end verification.

Đây là ranh giới module để sau này chia việc, **chưa phải lịch và phân công chính thức**.

## Source-of-truth

1. Functionality/field names: `SRS_CrawlInsight_10Days.md`.
2. API body and errors: `docs/API.md`.
3. SQLite structure: `database/schema.sql`.
4. Handoff evidence and pending checks: `docs/IMPLEMENTATION_STATUS.md`.
5. Build/install: `README.md`.

**Không đụng** các database, thư mục XAMPP hay project ngoài `CrawlInsight/`.
