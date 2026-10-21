# CrawlInsight — LTW-TH

**Web Programming & Applications (503073) · Midterm Topic 7: Web Crawling**  
**Source release:** V4.0 · Vietnamese-first bilingual web platform · Flask + Scrapy + SQLite

CrawlInsight is a multi-user web application that collects **real book data** from [Books to Scrape](https://books.toscrape.com/), explores it through filters and analytics, and offers private saved collections and preferences per user. Its crawler respects the allowed site and does **not** accept arbitrary external URLs. The real database has **no fake books** by default.

> This is runnable source code, **not** a hosted product. Local Flask/API and live scraping must be tested on a Windows computer after dependency installation. During source creation, 50 offline tests passed and 4 dependency-dependent tests were skipped because Flask/Scrapy could not be installed in the build environment. Before deploying publicly, perform security testing and use a production deployment setup.

## 1. What you can use

| URL | Audience | Role |
|---|---|---|
| `/` | Public | `index.html` landing page, feature introduction, how-to |
| `/register`, `/login` | Public | Account registration and authentication |
| `/forgot-password`, `/reset-password/<token>` | Public | Password recovery by SMTP, single-use 20-minute tokens |
| `/workspace` | Logged in | Dashboard, initiate crawl, live job monitor, rating charts |
| `/books` | Logged in | Source catalogue search, price filters, pagination, bookmarks, saved searches, details, CSV |
| `/saved` | Logged in | Personal saved books |
| `/history` | Logged in | Personal crawl history and job details |
| `/analytics` | Logged in | Real rating/category/price analytics |
| `/sources` | Logged in | Allowed source and responsible-crawling policy |
| `/settings` | Logged in | Name, password, language, theme, book layout |
| `/help` | Logged in | End-user help and onboarding |

The app UI has **Vietnamese (default) and English**, user-specific preferences and light/dark/system themes. Source-book titles/categories stay in their original language, and prices stay in **GBP** (not silently converted to Vietnamese đồng). Guests can explore the landing page without creating an account.

Security foundations: scrypt-salted password hashes, signed HttpOnly session cookies, CSRF tokens on mutations, login/recovery rate throttles, password recovery tokens stored as SHA-256 hashes, revocation of old sessions on password change/reset, scoped job history and bookmarks, cautious response headers, parameterized SQL, and server-side validation. Multi-user catalogue rows are shared; bookmarks, searches, job history and preferences are user-specific.

## 2. Install and launch on Windows

Requires **Python 3.11 or 3.12**, Internet for pip and crawling, Windows 10/11, and modern Chrome/Edge. XAMPP, PHP and MySQL are **not** required.

1. Unzip `LTW-TH_Source_V4.zip` so the root folder is exactly `LTW-TH` (you can place it in `C:\xampp\htdocs\LTW-TH`). If you already have a database from V3, **back it up before replacing source files**, and do not copy or overwrite the existing `data/` or private database.
2. Open `LTW-TH` and double-click **`START_HERE.bat`**. This runs `scripts/setup_windows.ps1` and starts the app.
3. Open **http://127.0.0.1:5000/**. You will see the new public landing page.
4. Choose **Đăng ký**, create your own account (no pre-seeded account is included), sign in, then open `/workspace` and start a crawl of **1 catalogue page**.
5. After a crawl completes, visit `/books`, `/analytics`, `/history`, and save some books to `/saved`.

**PowerShell alternative:**

```powershell
cd C:\xampp\htdocs\LTW-TH
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -c "from src.db import init_db; init_db()"
.\.venv\Scripts\python.exe app.py
```

Use `py -3.11` if Python 3.12 is unavailable. To change the Flask port create a `.env` file with `FLASK_PORT=5055`. The `.env` values are now read automatically by `app.py`. When copying from `.env.example`, do not commit the secret-bearing `.env` file.

**IMPORTANT:** `C:\xampp\htdocs\LTW-TH` is just a folder location for this Flask project. Do **not** open `http://localhost/LTW-TH` or assume that PHP/Apache will run it. Use `127.0.0.1:5000` (or the configured Flask port). `.htaccess` denies Apache requests where supported; it does not make exposing your whole source publicly safe.

## 3. Database V4 and migrations

- **15 persisted tables**: original 9 (`sources`, `categories`, `books`, `crawl_jobs`, `crawl_pages`, `crawl_job_books`, `book_price_history`, `crawl_events`, `schema_migrations`) plus 6 (`users`, `user_preferences`, `bookmarks`, `saved_searches`, `password_reset_tokens`, `auth_attempts`).
- **3 read-only views**: `v_books_detail`, `v_category_summary`, `v_job_overview`.
- **Migrations**: `database/migrations/001_core.sql`, `002_indexes.sql`, `003_views.sql`, `004_identity_and_workspace.sql`; SQLite reference snapshot `database/schema.sql` is V4, for **fresh** installations.
- `src/database/accounts.py` handles identity and preferences; existing `books.py`, `jobs.py` and `analytics.py` remain in place, with `src/db.py` preserving the crawler's existing imports.
- `init_db()` is idempotent. V2→V3 and V3→V4 upgrades preserve records and create a SQLite backup **before** changing an existing DB. Jobs created before V4 retain `user_id=NULL` and are not assigned to a newly registered account.

When project is inside XAMPP `htdocs`, runtime data is stored **outside htdocs**:

```text
C:\xampp\ltw-th-private-data\crawlinsight.db
C:\xampp\ltw-th-private-data\flask-session.key
C:\xampp\ltw-th-private-data\logs\crawl-job-<id>.log
```

Otherwise runtime SQLite defaults to `LTW-TH/data/crawlinsight.db`. Never commit those files or share session keys. To inspect real data:

```powershell
.\.venv\Scripts\python.exe -m database.tools.db_cli tables
.\.venv\Scripts\python.exe -m database.tools.db_cli rows users --limit 10
.\.venv\Scripts\python.exe -m database.tools.db_cli rows v_books_detail --limit 20
.\.venv\Scripts\python.exe -m database.tools.db_cli rows crawl_jobs --limit 20
.\.venv\Scripts\python.exe -m database.tools.db_cli check
```

**Privacy:** `users`, `password_reset_tokens` and other user tables contain personal or security-related material; only inspect locally and do **not** publish exported HTML/CSV snapshots. `database/examples/Database_Explorer_DEMO.html` and `CrawlInsight_DEMO.sqlite3` use synthetic DEMO-labelled book data and have no pre-seeded users. They are for studying the schema only.

## 4. Enable real forgot-password email

No default email credentials are bundled. Copy `.env.example` to `.env`, then configure SMTP. Example (Gmail App Password, TLS 587):

```dotenv
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-address@gmail.com
SMTP_FROM=your-address@gmail.com
SMTP_PASSWORD=your-app-password
ALLOW_LOCAL_RESET_LINKS=0
```

With valid SMTP configuration, the recovery form emails an HTTPS/localhost-link derived from the current trusted application host. The reset token is valid for **20 minutes** and only **once**. When SMTP is not configured, the UI **reports that email is unavailable**—it will not falsely claim that an email was sent.

**Local-only fallback for teammates without SMTP:** Set `ALLOW_LOCAL_RESET_LINKS=1` in `.env` and access Flask directly using `127.0.0.1`. After submitting an existing account email, a reset link appears **in the browser** solely for testing. Never use this setting on a public machine or server; set it back to `0` before deployment. With neither SMTP nor local fallback configured, password reset will return `503 MAIL_NOT_CONFIGURED`.

## 5. Run and verify tests

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

The suite includes migration regression (V2 and V3 to V4), book/job integrity, password hashing, session-version invalidation, expired/one-time reset tokens, duplicate email handling, bookmarks and saved searches isolated by user, template rendering in VI/EN and Flask API auth/CSRF smoke tests.

**Manual acceptance checklist (Windows with Flask/Scrapy installed):**

1. New visitor sees `/` without an account. Clicking CTA navigates to registration.
2. Register with a valid email + 10-character mixed password; log out, then log in again.
3. Confirm `/workspace`, `/books`, `/saved`, `/history`, `/analytics`, `/sources`, `/settings`, `/help` all load without console/network errors at desktop and mobile widths.
4. Select **1 page**, start a real crawl, observe state `PENDING → RUNNING → COMPLETED` and inspect records in SQLite. Repeat crawl and verify no duplicate book URL.
5. Filter books by title and original GBP price; bookmark a book and verify `/saved`.
6. Create a second account; the shared catalogue should still exist, but no personal bookmarks, saved searches or jobs from the first account should appear.
7. Change language and theme under `/settings`, refresh and sign in again; selections persist. Test book `list` view.
8. Export CSV and open in Excel; verify Vietnamese text encoded correctly and original GBP amounts.
9. Enable SMTP or explicit **local-only** password reset, use the token once, and verify reuse is rejected. Confirm previous login sessions are invalidated.
10. Run `python -m pytest -q`, validate in Chrome/Edge, and record errors with screenshot, traceback and reproduction steps.

## 6. Known constraints — no pretending these are already complete

- **Live Flask HTTP and Scrapy integration** require testing after installing dependencies; the build environment could not install them. `pytest.importorskip()` skipped the dependency-dependent cases, but Python/Jinja/JS source and database tests passed offline.
- SMTP email delivery depends on valid credentials, provider policy and network access; no account verification or transactional email service is bundled.
- Current source is deliberately restricted to **one permitted training website**, max **3 catalogue pages per crawl**, one active job globally. It is not a generic multi-domain crawler.
- Book metadata, ratings and GBP price are retained as source observations; there is no translation of scraped content and no currency-conversion API.
- This is a **local-first development configuration**. Public production hosting needs HTTPS, trusted host/proxy review, hardened session and secret management, backup/retention, application security audit and monitoring.

More details: `PROJECT_STRUCTURE.md`, `docs/IMPLEMENTATION_STATUS_V4.md`, `docs/API_V4.md`, `database/DATA_DICTIONARY.md`. The earlier **SRS 2.0** remains the baseline for crawling logic; it has **not yet been fully revised** to reflect the expanded account/workspace scope.
