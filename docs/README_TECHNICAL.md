# CrawlInsight — Setup and Operations

## Requirements

- Windows 10/11
- PHP 8.2 or newer with the SQLite PDO extension enabled
- Composer
- Python 3.11 or 3.12 for the Scrapy worker
- Internet access for dependency installation and live crawling

## Windows quick start

1. Install PHP and Composer and make both available on `PATH`.
2. Run `START_HERE.bat`, or run `scripts/setup_windows.ps1` followed by `scripts/start_windows.ps1`.
3. Open `http://127.0.0.1:8000/`.
4. Register a user and start a one-page crawl from the workspace.

Setup creates `.env` from `.env.example` only when it does not already exist, installs Composer and Python dependencies, generates an application key if missing, and initializes the SQLite database without deleting existing data.

## Shared database configuration

Set `CRAWLINSIGHT_DB_PATH` in `.env` to the desired SQLite file. Relative paths resolve from the repository root. Laravel resolves the configured path and passes it explicitly to the Python worker; do not set a different path for one runtime. The default database is outside the repository when it is under an Apache `htdocs` directory.

Back up the database before schema upgrades. Stop Laravel and the crawler before performing manual migration or restore operations. The schema and migrations under `database/` remain authoritative.

## Password reset email

Configure `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD`, `SMTP_FROM`, and `SMTP_SCHEME` in the local `.env` file. Never commit real SMTP credentials. Reset links are time-limited and single-use. `ALLOW_LOCAL_RESET_LINKS=1` is intended only for explicitly opted-in loopback testing.

## Testing

Run both language test suites:

```powershell
.\scripts\run_tests_windows.ps1
```

The script runs Python crawler/database tests with pytest and Laravel feature tests through Composer/PHPUnit. It requires the setup step to have completed successfully.

## Runtime boundaries

- Laravel/PHP serves every web page and API route.
- Python/Scrapy is started only as a crawler worker.
- SQLite is shared; the Python worker must not be launched with a different database path.
- `app.py` remains only as a compatibility launcher that delegates to `php artisan serve`.
- Do not expose the repository or SQLite database through Apache or another static file server.

## Migration validation caveat

When the migration code was authored, PHP and Composer were unavailable, so PHP linting, Composer resolution, PHPUnit, Twig rendering, HTTP flows, SMTP, and Windows subprocess execution had not yet been verified. Treat those as pending until the test and acceptance steps above have been run on a configured machine.
