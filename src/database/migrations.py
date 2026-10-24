"""Versioned, transactional, NON-DESTRUCTIVE schema bootstrap/legacy upgrade.

Migrates the original SRS 2.0 two-table schema without losing books or jobs.
Copies a backup BEFORE modifying a legacy database. Does not insert fake books.
"""
from __future__ import annotations
import sqlite3
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from .connection import (
    MIGRATIONS_DIR, MYSQL_SCHEMA_PATH, ROOT, connect, database_path, now_utc,
)

FILES = (
    '001_core.sql',
    '002_indexes.sql',
    '003_views.sql',
    '004_identity_and_workspace.sql',
    '005_price_change_notifications.sql',
    '006_user_isolation_and_admin.sql',
)
SOURCE_NAME = 'Books to Scrape'
SOURCE_URL = 'https://books.toscrape.com/'
SOURCE_HOST = 'books.toscrape.com'


def _backup_legacy(connection: sqlite3.Connection) -> Path:
    p = database_path()
    out = p.with_name(f'{p.stem}.before-v3-{datetime.now(timezone.utc):%Y%m%dT%H%M%SZ}.sqlite3')
    if out.exists():
        raise FileExistsError(f'Backup already exists: {out}')
    target = sqlite3.connect(str(out))
    try:
        connection.backup(target)
    finally:
        target.close()
    return out


def init_db() -> None:
    """Creates or upgrades the database through the latest version idempotently."""
    if os.environ.get('DB_CONNECTION', 'mysql').strip().lower() == 'mysql':
        _init_mysql()
        return
    con = connect()
    try:
        con.execute('PRAGMA journal_mode=WAL')
        tables = {r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        is_legacy = {'books', 'crawl_jobs'} <= tables and 'sources' not in tables
        if is_legacy:
            _backup_legacy(con)
        if 'sources' in tables and 'schema_migrations' not in tables:
            raise RuntimeError('Unrecognized source database version; refusing unsafe upgrade')
        if not is_legacy and 'sources' in tables:
            versions = {int(r[0]) for r in con.execute('SELECT version FROM schema_migrations')}
            if versions not in (
                {1, 2, 3},
                {1, 2, 3, 4},
                {1, 2, 3, 4, 5},
                {1, 2, 3, 4, 5, 6},
            ):
                raise RuntimeError(f'Incomplete/unrecognized migration history: {versions}')
            if versions == {1, 2, 3}:
                _backup_v3(con)
                _apply_identity_upgrade(con)
            _apply_notifications_upgrade(con)
            _apply_user_isolation_upgrade(con)
            issues=con.execute('PRAGMA foreign_key_check').fetchall()
            if issues: raise RuntimeError(f'Foreign key check failed: {issues}')
            return

        commands = ['BEGIN IMMEDIATE;']
        if is_legacy:
            commands += [
                'ALTER TABLE books RENAME TO __books_v2;',
                'ALTER TABLE crawl_jobs RENAME TO __crawl_jobs_v2;',
                'DROP INDEX IF EXISTS idx_books_title;',
                'DROP INDEX IF EXISTS idx_books_price;',
                'DROP INDEX IF EXISTS idx_jobs_created;',
            ]
        commands.append((MIGRATIONS_DIR / FILES[0]).read_text(encoding='utf-8'))
        created = now_utc()
        commands.append(
            "INSERT INTO sources(id,name,base_url,allowed_host,is_enabled,created_at) "
            "VALUES(1,'Books to Scrape','https://books.toscrape.com/'," 
            f"'books.toscrape.com',1,'{created}');"
        )
        if is_legacy:
            commands += [
                "INSERT OR IGNORE INTO categories(source_id,name,first_seen_at) "
                "SELECT 1,trim(category),MIN(first_seen_at) FROM __books_v2 "
                "GROUP BY category;",
                "INSERT INTO crawl_jobs(id,source_id,max_pages,status,catalogue_pages_done," 
                "books_found,items_saved,new_books,existing_books,error_count,last_error," 
                "created_at,started_at,finished_at) SELECT id,1,max_pages,status," 
                "catalogue_pages_done,books_found,items_saved,new_books,existing_books," 
                "error_count,last_error,created_at,started_at,finished_at FROM __crawl_jobs_v2;",
                "INSERT INTO books(id,source_id,category_id,source_url,title,price_pence,rating," 
                "availability,image_url,upc,first_seen_at,last_seen_at,last_crawl_job_id) " 
                "SELECT b.id,1,c.id,b.source_url,b.title,b.price_pence,b.rating," 
                "b.availability,b.image_url,b.upc,b.first_seen_at,b.last_seen_at,NULL " 
                "FROM __books_v2 b JOIN categories c ON c.source_id=1 AND c.name=trim(b.category) COLLATE NOCASE;",
                'DROP TABLE __books_v2;',
                'DROP TABLE __crawl_jobs_v2;',
            ]
        commands.append((MIGRATIONS_DIR / FILES[1]).read_text(encoding='utf-8'))
        commands.append((MIGRATIONS_DIR / FILES[2]).read_text(encoding='utf-8'))
        for index, filename in enumerate(FILES[:3], 1):
            commands.append(
                f"INSERT INTO schema_migrations(version,filename,applied_at) "
                f"VALUES({index},'{filename}','{created}');"
            )
        commands.append('PRAGMA user_version=3;')
        commands.append('COMMIT;')
        try:
            con.executescript('\n'.join(commands))
        except BaseException:
            if con.in_transaction:
                con.rollback()
            raise
        _apply_identity_upgrade(con)
        _apply_notifications_upgrade(con)
        _apply_user_isolation_upgrade(con)
        bad_fks = con.execute('PRAGMA foreign_key_check').fetchall()
        if bad_fks:
            raise RuntimeError(f'Schema created but foreign key check failed: {bad_fks}')
    finally:
        con.close()


def _apply_identity_upgrade(con: sqlite3.Connection) -> None:
    """Apply v4 atomically after a v3 bootstrap, preserving every legacy row."""
    existing = con.execute('SELECT 1 FROM schema_migrations WHERE version=4').fetchone()
    if existing:
        return
    script = (MIGRATIONS_DIR / FILES[3]).read_text(encoding='utf-8')
    when = now_utc()
    # executescript commits pending statements; script itself owns the transaction.
    con.executescript('BEGIN IMMEDIATE;\n' + script + '\n' +
        "INSERT INTO schema_migrations(version,filename,applied_at) VALUES(4,'004_identity_and_workspace.sql','" + when + "');\n" +
        'PRAGMA user_version=4;\nCOMMIT;')


def _apply_notifications_upgrade(con: sqlite3.Connection) -> None:
    """Add per-user price change notifications to v4 databases."""
    existing = con.execute('SELECT 1 FROM schema_migrations WHERE version=5').fetchone()
    if existing:
        return
    script = (MIGRATIONS_DIR / FILES[4]).read_text(encoding='utf-8')
    when = now_utc()
    con.executescript(
        'BEGIN IMMEDIATE;\n' + script + '\n'
        "INSERT INTO schema_migrations(version,filename,applied_at) "
        "VALUES(5,'005_price_change_notifications.sql','" + when + "');\n"
        'PRAGMA user_version=5;\nCOMMIT;'
    )


def _backup_v3(connection: sqlite3.Connection) -> Path:
    p=database_path()
    out=p.with_name(f'{p.stem}.before-v4-{datetime.now(timezone.utc):%Y%m%dT%H%M%SZ}.sqlite3')
    if out.exists():raise FileExistsError(f'Backup already exists: {out}')
    target=sqlite3.connect(str(out))
    try:connection.backup(target)
    finally:target.close()
    return out


def _apply_user_isolation_upgrade(con: sqlite3.Connection) -> None:
    """Give every account an isolated book catalog and add administrator roles."""
    existing = con.execute('SELECT 1 FROM schema_migrations WHERE version=6').fetchone()
    if existing:
        return
    con.commit()
    _backup_v5(con)
    script = (MIGRATIONS_DIR / FILES[5]).read_text(encoding='utf-8')
    con.executescript(script.replace('__APPLIED_AT__', now_utc()))


def _backup_v5(connection: sqlite3.Connection) -> Path:
    p = database_path()
    out = p.with_name(f'{p.stem}.before-v6-{datetime.now(timezone.utc):%Y%m%dT%H%M%SZ}.sqlite3')
    if out.exists():
        raise FileExistsError(f'Backup already exists: {out}')
    target = sqlite3.connect(str(out))
    try:
        connection.backup(target)
    finally:
        target.close()
    return out


def _init_mysql() -> None:
    import pymysql

    database = os.environ.get('DB_DATABASE', 'crawlinsight').strip()
    if not re.fullmatch(r'[A-Za-z0-9_]+', database):
        raise ValueError('DB_DATABASE may contain only letters, numbers, and underscores')
    host = os.environ.get('DB_HOST', '127.0.0.1')
    port = int(os.environ.get('DB_PORT', '3308'))
    username = os.environ.get('DB_USERNAME', 'root')
    password = os.environ.get('DB_PASSWORD', '')
    server = pymysql.connect(
        host=host, port=port, user=username, password=password,
        charset='utf8mb4', autocommit=True, connect_timeout=5,
    )
    try:
        with server.cursor() as cursor:
            cursor.execute(
                f'CREATE DATABASE IF NOT EXISTS `{database}` '
                'CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci'
            )
    finally:
        server.close()

    schema = MYSQL_SCHEMA_PATH.read_text(encoding='utf-8')
    with connect() as con:
        for statement in schema.split(';'):
            statement = statement.strip()
            if statement:
                con.execute(statement)
        for version, filename in enumerate(FILES, 1):
            con.execute(
                'INSERT IGNORE INTO schema_migrations(version,filename,applied_at) VALUES(?,?,?)',
                (version, filename, now_utc()),
            )

    _import_legacy_sqlite()
    _seed_mysql_sources()


def _import_legacy_sqlite() -> None:
    configured = os.environ.get('CRAWLINSIGHT_SQLITE_IMPORT', '').strip()
    path = Path(configured).expanduser().resolve() if configured else database_path()
    if not path.is_file():
        return

    source = sqlite3.connect(str(path))
    source.row_factory = sqlite3.Row
    try:
        tables = {
            row['name'] for row in source.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            )
        }
        if not {'sources', 'users', 'books', 'crawl_jobs'} <= tables:
            return
        versions = {
            int(row[0]) for row in source.execute(
                'SELECT version FROM schema_migrations'
            )
        } if 'schema_migrations' in tables else set()
    finally:
        source.close()

    if versions != {1, 2, 3, 4, 5, 6}:
        previous_driver = os.environ.get('DB_CONNECTION')
        previous_path = os.environ.get('CRAWLINSIGHT_DB_PATH')
        previous_import = os.environ.get('CRAWLINSIGHT_SQLITE_IMPORT')
        try:
            os.environ['DB_CONNECTION'] = 'sqlite'
            os.environ['CRAWLINSIGHT_DB_PATH'] = str(path)
            os.environ.pop('CRAWLINSIGHT_SQLITE_IMPORT', None)
            init_db()
        finally:
            if previous_driver is None:
                os.environ.pop('DB_CONNECTION', None)
            else:
                os.environ['DB_CONNECTION'] = previous_driver
            if previous_path is None:
                os.environ.pop('CRAWLINSIGHT_DB_PATH', None)
            else:
                os.environ['CRAWLINSIGHT_DB_PATH'] = previous_path
            if previous_import is None:
                os.environ.pop('CRAWLINSIGHT_SQLITE_IMPORT', None)
            else:
                os.environ['CRAWLINSIGHT_SQLITE_IMPORT'] = previous_import

        source = sqlite3.connect(str(path))
        try:
                tables = {
                    row[0] for row in source.execute(
                        "SELECT name FROM sqlite_master WHERE type='table'"
                    )
                }
        finally:
                source.close()

    with connect() as target:
        imported = target.execute(
            'SELECT 1 FROM legacy_imports WHERE source_path=?', (str(path),)
        ).fetchone()
        if imported:
            return
        import_tables = (
            'users', 'categories', 'crawl_jobs', 'books', 'user_preferences',
            'crawl_pages', 'crawl_events', 'crawl_job_books', 'book_price_history',
            'bookmarks', 'saved_searches', 'password_reset_tokens',
            'auth_attempts', 'price_change_notifications',
        )
        existing = sum(
            target.execute(f'SELECT COUNT(*) FROM `{table}`').fetchone()[0]
            for table in import_tables
        )
        if existing:
            raise RuntimeError(
                'MySQL already contains user data; refusing to mix it with the SQLite import.'
            )
        target.execute('DELETE FROM sources')

        order = (
            'sources', 'users', 'categories', 'crawl_jobs', 'books',
            'user_preferences', 'crawl_pages', 'crawl_events', 'crawl_job_books',
            'book_price_history', 'bookmarks', 'saved_searches',
            'password_reset_tokens', 'auth_attempts', 'price_change_notifications',
        )
        source = sqlite3.connect(str(path))
        source.row_factory = sqlite3.Row
        try:
            for table in order:
                if table not in tables:
                    continue
                target_columns = {
                    row['Field'] for row in target.execute(f'SHOW COLUMNS FROM `{table}`')
                    if 'generated' not in row['Extra'].lower()
                }
                source_columns = [
                    column['name'] for column in source.execute(f'PRAGMA table_info("{table}")')
                    if column['name'] in target_columns
                ]
                if table == 'books' and 'source_url_hash' in target_columns and 'source_url_hash' not in source_columns:
                    source_columns.append('source_url_hash')
                if not source_columns:
                    continue
                columns = ','.join(f'`{column}`' for column in source_columns)
                placeholders = ','.join('?' for _ in source_columns)
                statement = f'INSERT INTO `{table}` ({columns}) VALUES ({placeholders})'
                rows = source.execute(f'SELECT * FROM `{table}`')
                for row in rows:
                    values = [
                        row[column] for column in source_columns
                        if column != 'source_url_hash'
                    ]
                    if table == 'books':
                        import hashlib
                        source_url = row['source_url']
                        values.append(hashlib.sha256(source_url.encode('utf-8')).hexdigest())
                    target.execute(statement, values)
        except Exception:
            target.rollback()
            raise
        finally:
            source.close()
        target.execute(
            'INSERT INTO legacy_imports(source_path,imported_at) VALUES(?,?)',
            (str(path), now_utc()),
        )


def _seed_mysql_sources() -> None:
    sources = (
        (1, 'Books to Scrape', 'https://books.toscrape.com/', 'books.toscrape.com'),
        (2, 'Open Library', 'https://openlibrary.org/', 'openlibrary.org'),
        (3, 'Project Gutenberg', 'https://www.gutenberg.org/', 'www.gutenberg.org'),
    )
    with connect() as con:
        if con.execute('SELECT COUNT(*) FROM sources').fetchone()[0]:
            return
        for source_id, name, url, host in sources:
            con.execute(
                'INSERT INTO sources(id,name,base_url,allowed_host,is_enabled,created_at) '
                'VALUES(?,?,?,?,1,?)',
                (source_id, name, url, host, now_utc()),
            )
