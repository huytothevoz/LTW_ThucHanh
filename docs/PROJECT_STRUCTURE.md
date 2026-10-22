# LTW-TH — Project Structure

```text
LTW-TH/
├── artisan                           # Laravel command-line entry
├── app/
│   ├── Http/Controllers/             # Page, static asset, and JSON API controllers
│   ├── Http/Middleware/              # Identity, authentication, and security headers
│   ├── Services/                     # PHP account, books, and crawl-job logic
│   └── Support/TwigRenderer.php       # Renders the shared Twig templates
├── bootstrap/                        # Laravel application initialization
├── config/                           # App, SQLite, session, mail, and logging config
├── routes/web.php                    # HTML and JSON routes with Laravel web/CSRF middleware
├── public/                           # Laravel public entry point; source assets stay outside
├── templates/                        # Twig-rendered landing, auth, and workspace pages
├── static/
│   ├── css/                          # Application styling and dark mode
│   ├── js/                           # Browser API clients and page controllers
│   └── img/                          # Local images and favicon
├── crawler/                          # Python Scrapy spider, parser, pipeline, worker
├── src/
│   ├── db.py                         # Stable Python SQLite facade for the worker
│   └── database/                     # Python-side connection, migrations, books, jobs
├── database/
│   ├── schema.sql                    # V4 fresh-install SQL reference
│   ├── migrations/                   # Additive SQL migrations 001–004
│   ├── tools/                        # Database inspection and export utilities
│   └── examples/                     # Synthetic demo data and viewers
├── tests/
│   ├── php/                          # Laravel/PHPUnit feature tests
│   └── *.py                          # Python crawler/database tests
├── scripts/                          # Windows setup, start, and combined test scripts
├── docs/                             # Architecture, API, requirements, and status
├── composer.json                     # Laravel, Twig, scrypt, PHPUnit
└── requirements.txt                  # Scrapy and pytest only
```

## Ownership and integration

- **Laravel/PHP** is the only web backend. It owns identity/session security, JSON APIs, Twig pages, account services, and asynchronous job launch.
- **Python** is retained for Scrapy and the crawler's SQLite persistence. The Python worker is launched as `python -m crawler.run_job --job-id N`.
- Both processes use one database file. Configure `CRAWLINSIGHT_DB_PATH` in `.env`; Laravel passes its resolved value to the crawler.
- `database/schema.sql` and numbered migrations remain authoritative. The PHP application uses the existing V4 schema rather than creating a second set of tables.
- Do not move SQLite files or `.env` into the public directory. Runtime logs and session files are private.

## Database isolation

- Shared source data: books, categories, sources, price history, and crawl evidence.
- User-scoped data: users, preferences, bookmarks, saved searches, and owned crawl jobs.
- Reset tokens and authentication attempt identifiers are stored hashed.
- Legacy jobs migrated from earlier schema versions keep `user_id IS NULL`; do not attach historical jobs to new users.
