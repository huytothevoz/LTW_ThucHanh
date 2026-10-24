# CrawlInsight Database — MySQL/MariaDB

Laravel and the Python Scrapy worker use the same MySQL/MariaDB database. The Windows/XAMPP setup defaults to `127.0.0.1:3308`, database `crawlinsight`, username `root`, and an empty password. Configure the connection in the local `.env` file; never commit credentials.

## Quick setup

1. Double-click `START_HERE.bat`.
2. Setup starts XAMPP MariaDB if needed, installs dependencies, creates/updates the MySQL schema, imports the previous SQLite database once if present, then starts Laravel.
3. Register an account and run a crawl. A new database contains source metadata and schema migrations, but no sample users or books.

PHP must have `pdo_mysql` enabled. The Python worker installs PyMySQL from `requirements.txt`. Both processes receive the connection settings from `.env`.

### Automatic XAMPP startup

The launcher starts `mysqld.exe` directly with XAMPP's existing `my.ini`; the Control Panel does not need to be open. It binds XAMPP MariaDB to port `3308`, separately from other MySQL services such as MySQL80 on port `3306`. It reuses MariaDB already running on `3308`, but will not connect to a different MySQL server. Setup uses the local XAMPP `root` account without a password and does not alter other MySQL service accounts. It never edits XAMPP's global configuration. Set `XAMPP_HOME` if XAMPP is installed somewhere other than `C:\xampp`; startup logs are saved under `storage\logs`.

## Connection and legacy import

The active connection keys are:

```dotenv
DB_CONNECTION=mysql
DB_HOST=127.0.0.1
DB_PORT=3308
DB_DATABASE=crawlinsight
DB_USERNAME=root
DB_PASSWORD=
```

On the first setup, the importer checks `CRAWLINSIGHT_SQLITE_IMPORT`; if blank, it checks the former `CRAWLINSIGHT_DB_PATH` and the old default file location (`data\crawlinsight.db`, or the previous private XAMPP location). Existing SQLite data is copied to MySQL without deleting the SQLite file. A SQLite file that needs an earlier schema upgrade is backed up before that upgrade. The import is recorded in MySQL and will not be repeated on later setup runs.

The importer refuses to merge SQLite rows into a MySQL database that already has users, books, or crawl jobs. Back up MySQL before any manual import. If no old SQLite database exists, setup creates a clean MySQL schema.

## Schema ownership

- [`mysql_schema.sql`](mysql_schema.sql) is the runtime MySQL/MariaDB schema and is applied idempotently by `src.database.migrations.init_db()`.
- [`schema.sql`](schema.sql) and [`migrations/`](migrations) are retained only for SQLite legacy upgrades and isolated SQLite tests; the web app and crawler do not use them at runtime.
- MySQL stores the current V6 data model and schema migration history. Books and jobs are scoped by `user_id`; admin role management is documented in the root README.
- Per-user book URLs are indexed by a SHA-256 digest to preserve full-length source URLs without exceeding MySQL index-size limits. An active-job generated key enforces one pending/running job per account.
- Database rows use InnoDB, `utf8mb4`, and UTC ISO-8601 text timestamps. Prices remain integer GBP pence.

See [`DATA_DICTIONARY.md`](DATA_DICTIONARY.md) for table fields and relationships, and [`SQL_RECIPES.md`](SQL_RECIPES.md) for phpMyAdmin-compatible queries.

## Inspect and export MySQL

Run from the repository root after setup:

```powershell
.\.venv\Scripts\python.exe -m database.tools.db_cli init
.\.venv\Scripts\python.exe -m database.tools.db_cli tables
.\.venv\Scripts\python.exe -m database.tools.db_cli check
.\.venv\Scripts\python.exe -m database.tools.db_cli describe books
.\.venv\Scripts\python.exe -m database.tools.db_cli rows books --limit 10
.\.venv\Scripts\python.exe -m database.tools.db_cli export v_books_detail --format csv --output "$env:TEMP\books.csv"
```

The inspection commands use the configured MySQL connection. For a full backup, use phpMyAdmin **Export** or `mysqldump`; do not copy SQLite backup procedures onto the live MySQL database.

## Existing account and catalog isolation

The SQLite V6 migration copies shared books for owners represented by crawl observations, bookmarks, or price notifications. Legacy records with no known owner remain unassigned instead of being exposed to a newly registered user. Source and category metadata remain shared. The MySQL schema preserves these owner IDs during import.

When upgrading an important database, stop Laravel and crawler workers first, export a MySQL backup, run setup, and verify the imported users, books, jobs, and foreign-key relationships in phpMyAdmin or with `db_cli check`.
