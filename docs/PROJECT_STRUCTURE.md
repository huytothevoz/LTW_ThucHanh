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
├── config/                           # App, MySQL, session, mail, and logging config
├── routes/web.php                    # HTML and JSON routes with Laravel web/CSRF middleware
├── public/                           # Laravel public entry point; source assets stay outside
├── templates/                        # Twig-rendered landing, auth, and workspace pages
├── static/
│   ├── css/                          # Application styling and dark mode
│   ├── js/                           # Browser API clients and page controllers
│   └── img/                          # Local images and favicon
├── crawler/                          # Python Scrapy spider, parser, pipeline, worker
├── src/
│   ├── db.py                         # Stable Python MySQL facade for the worker
│   └── database/                     # MySQL connection, schema/import, books, jobs
├── database/
│   ├── mysql_schema.sql              # Runtime MySQL/MariaDB schema
│   ├── schema.sql                    # Legacy SQLite schema for import/tests only
│   ├── migrations/                   # Legacy SQLite upgrades and test fixtures
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
- **Python** is retained for Scrapy and the crawler's MySQL persistence. The Python worker is launched as `python -m crawler.run_job --job-id N`.
- Both processes use one MySQL/MariaDB database. Configure `DB_HOST`, `DB_PORT`, `DB_DATABASE`, `DB_USERNAME`, and `DB_PASSWORD` in `.env`; Laravel passes these values to the crawler.
- `database/mysql_schema.sql` is authoritative at runtime. SQLite schema/migrations are retained only to upgrade and import old SQLite data and for isolated tests.
- Keep `.env` private. Runtime logs and session files are private.

## Database isolation

- Shared source data: books, categories, sources, price history, and crawl evidence.
- User-scoped data: users, preferences, bookmarks, saved searches, and owned crawl jobs.
- Reset tokens and authentication attempt identifiers are stored hashed.
- Legacy jobs migrated from earlier schema versions keep `user_id IS NULL`; do not attach historical jobs to new users.
