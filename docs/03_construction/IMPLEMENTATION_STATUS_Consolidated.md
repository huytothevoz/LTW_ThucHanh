# CrawlInsight — Implementation Status & Handoff

**Current migration:** Flask/Python web backend → Laravel/PHP; Python/Scrapy crawler retained.
**Status:** Migration source is implemented but **not runtime-validated**.
**Runtime limitation:** PHP and Composer are unavailable in the implementation environment; no Composer install, PHP lint, PHPUnit, Laravel startup, HTTP, SMTP, or Windows crawler-launch validation has been performed.

**Database update (2026-10-24):** Runtime persistence has been switched to MySQL/MariaDB on XAMPP port 3306. Windows setup creates the schema and can import a prior SQLite database once; SQLite migrations remain only for that legacy import and isolated tests. Validate this path against a running XAMPP instance before release.

## 1. Current component ownership

| Component | Current owner | Status |
|---|---|---|
| Web routes, API, authentication/session/CSRF | Laravel 12 / PHP 8.2+ | Source added; runtime verification pending |
| Server-rendered pages | Twig templates through Laravel renderer | Adapted; render compatibility pending |
| Browser UI and API calls | HTML/CSS/JavaScript | Existing UI retained; browser/E2E pending |
| Crawler requests and HTML parsing | Python 3.11/3.12 + Scrapy | Retained |
| Crawler-side MySQL writes | Python `src.db` and `src/database/` | Implemented; XAMPP integration pending |
| Shared persistence | MySQL/MariaDB V6 schema | Runtime default switched; cross-runtime check pending |
| Windows setup/start/test | PowerShell scripts | Updated for PHP/Composer and Python worker; not executed |

The old Flask route modules and Python account service have been removed. `app.py` is a compatibility launcher only; Laravel is the web application entry point.

## 2. Migration implementation

- Added Laravel project scaffolding, configuration, route registration, security headers, identity resolution, authenticated-route guard, and a Twig renderer.
- Added API handlers for health, identity, registration/login/logout, reset-password, profile/preferences/password, crawl jobs, books, bookmarks, saved searches, history, analytics, sources, and CSV export.
- Added PHP services for account/password management, book queries/analytics, and asynchronous crawler job creation.
- The SQLite V4 schema was preserved for legacy upgrade/import; runtime MySQL is defined in `database/mysql_schema.sql`. PHP and Python share the same `DB_*` settings, passed to the crawler child process.
- Updated Windows setup/start/test scripts and the README, architecture, project structure, API, coding conventions, database, and concept documentation.
- Removed obsolete Flask web handlers, Python account handlers, and their Flask/Jinja-specific tests. Added a minimal PHPUnit API health/404 contract test.

## 3. Validation record

| Check | Result |
|---|---|
| Repository/source inspection | Completed |
| Python crawler/database automated tests | Not run in this migration turn |
| PHP syntax/lint | Not run: PHP unavailable |
| Composer dependency resolution | Not run: Composer unavailable |
| PHPUnit/Laravel feature tests | Not run: PHP/Composer unavailable |
| Twig template rendering | Not run: PHP/Composer unavailable |
| Browser, HTTP, SMTP, live crawl, Windows process integration | Not run |

Do not report the migration as complete for release until the validation checklist below passes on a machine with the required toolchains.

## 4. Required acceptance work

1. Run `scripts/setup_windows.ps1` on a clean Windows 10/11 machine with PHP 8.2+, Composer, and Python 3.11/3.12.
2. Run `scripts/run_tests_windows.ps1`; fix all PHP/Python failures and record exact results.
3. Verify a fresh MySQL schema, a one-time import from existing SQLite data, foreign-key relationships, and that PHP and Python connect to the same MySQL database on port 3306.
4. Test register → login → CSRF-protected mutation → logout, preferences, reset token expiry/one-time use, and owner isolation using HTTP cookies.
5. Verify Twig page rendering and all UI routes in a browser in Vietnamese and English, including mobile and dark mode.
6. Create a job, verify asynchronous worker startup and logs, poll status/events, and confirm one-active-job behavior.
7. Test SMTP success/failure and CSV output in spreadsheet software, including formula-prefixed cells.
8. Update the API/SRS acceptance evidence and this status file only after the relevant test actually passes.

## 5. Known risks to resolve during validation

- PHP scrypt package output must be verified against stored Python `hashlib.scrypt` hashes (`N=16384, r=8, p=1, dklen=64`) before existing accounts are considered compatible.
- Twig/Jinja compatibility, including macros, tuple loops, escaping, and filters, has not been rendered with Twig.
- MySQL/MariaDB DDL, generated columns, schema import ordering, PDO/PyMySQL connections, and XAMPP port 3306 need runtime confirmation.
- Windows PowerShell background process startup, redirected logs, and environment inheritance need a real crawl test.
- CSV formula-prefix handling is implemented but not yet validated in Excel/LibreOffice.

## 6. Canonical documentation

- API contract: [`API_CrawlInsight_Consolidated.md`](../02_elaboration/API_CrawlInsight_Consolidated.md)
- Architecture: [`ARCHITECTURE.md`](../ARCHITECTURE.md)
- Project map: [`PROJECT_STRUCTURE.md`](../PROJECT_STRUCTURE.md)
- Setup and operations: [`README_TECHNICAL.md`](../README_TECHNICAL.md)
- Database schema: [`schema.sql`](../../database/schema.sql)
