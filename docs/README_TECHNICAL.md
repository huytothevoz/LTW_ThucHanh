# CrawlInsight — Setup and Operations

## Requirements

- Windows 10/11
- PHP 8.2+ with `pdo_mysql` enabled
- Composer
- Python 3.11 or 3.12
- XAMPP installed at `C:\xampp` (or set `XAMPP_HOME` to its installation directory)
- Internet access for dependency installation and crawling

## Windows quick start

1. Double-click `START_HERE.bat`.
2. The setup starts XAMPP MariaDB if needed, prepares/imports the database, then starts Laravel.
3. Open `http://127.0.0.1:8000/`, register a user, and start a one-page crawl.

The launcher does not require XAMPP Control Panel to be open. It starts XAMPP `mysqld.exe` directly using the existing XAMPP `my.ini` on port `3306`, or reuses the same XAMPP instance if it is already running. It never starts a second server against the same data directory and refuses to connect to a different MySQL service on `3306`. It never edits XAMPP's global configuration or deletes the SQLite file. If XAMPP is installed outside `C:\xampp`, set `XAMPP_HOME` to its installation directory.

Setup updates SQLite connection settings to MySQL, configures this local project for XAMPP `root` without a password on port `3306`, installs Composer/Python dependencies, generates an application key, creates the `crawlinsight` database/schema and imports the previous SQLite file once when found. It does not change SMTP settings such as `SMTP_PASSWORD` for Gmail OTP delivery. Startup diagnostics are written under `storage\logs` if MariaDB fails to start.

The application uses the XAMPP default port `3306`. If another MySQL service already owns that port, setup stops with an explicit error; it does not change or reconfigure that service. Setup resets this project's `DB_PASSWORD` to empty for the selected local XAMPP `root` account.

## Shared MySQL configuration

Laravel and Python use the same environment variables:

```dotenv
DB_CONNECTION=mysql
DB_HOST=127.0.0.1
DB_PORT=3306
DB_DATABASE=crawlinsight
DB_USERNAME=root
DB_PASSWORD=
```

The schema is created by `python -m database.tools.db_cli init` or the Windows setup. `database/mysql_schema.sql` is the runtime MySQL schema; the older SQLite schema and migration scripts are retained only to upgrade/import SQLite files and to run isolated legacy tests.

To migrate existing SQLite records, set `CRAWLINSIGHT_SQLITE_IMPORT` to the file path. If it is blank, setup checks the old `CRAWLINSIGHT_DB_PATH` and the former default SQLite location. A needed SQLite schema upgrade creates a timestamped backup first. Import runs once and refuses to mix rows into a MySQL database that already contains users, books, or crawl jobs.

## Database inspection

Use the Python CLI or phpMyAdmin:

```powershell
.\.venv\Scripts\python.exe -m database.tools.db_cli tables
.\.venv\Scripts\python.exe -m database.tools.db_cli check
.\.venv\Scripts\python.exe -m database.tools.db_cli rows v_books_detail --limit 20
```

For a backup, use phpMyAdmin **Export** or `mysqldump`. Stop Laravel and crawler workers before restore or schema changes.

## Password reset email

Configure `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD`, `SMTP_FROM`, and `SMTP_SCHEME` in local `.env`. Never commit SMTP credentials. Reset links are time-limited and single-use. `ALLOW_LOCAL_RESET_LINKS=1` is intended only for explicitly opted-in loopback testing.

## Testing

Run both language test suites:

```powershell
.\scripts\run_tests_windows.ps1
```

PHP feature tests and isolated Python tests use SQLite in-memory/temp databases for speed. This does not change the MySQL runtime default. MySQL-specific bootstrap/import behavior should also be verified against XAMPP on port 3306.

## Runtime boundaries

- Laravel/PHP serves every web page and API route.
- Python/Scrapy is started only as a crawler worker.
- MySQL/MariaDB is shared; both processes must use the same `.env` connection values.
- `app.py` remains only as a compatibility launcher that delegates to `php artisan serve`.
- Do not expose the repository or database credentials through Apache or another static file server.
