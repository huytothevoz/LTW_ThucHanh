"""Versioned, transactional, NON-DESTRUCTIVE schema bootstrap/legacy upgrade.

Migrates the original SRS 2.0 two-table schema without losing books or jobs.
Copies a backup BEFORE modifying a legacy database. Does not insert fake books.
"""
from __future__ import annotations
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from .connection import MIGRATIONS_DIR, connect, database_path, now_utc

FILES = ('001_core.sql', '002_indexes.sql', '003_views.sql', '004_identity_and_workspace.sql')
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
    """Creates fresh v3 or upgrades v2. Calling multiple times is safe."""
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
            if versions not in ({1, 2, 3}, {1, 2, 3, 4}):
                raise RuntimeError(f'Incomplete/unrecognized migration history: {versions}')
            if versions == {1, 2, 3}:
                _backup_v3(con)
                _apply_identity_upgrade(con)
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


def _backup_v3(connection: sqlite3.Connection) -> Path:
    p=database_path()
    out=p.with_name(f'{p.stem}.before-v4-{datetime.now(timezone.utc):%Y%m%dT%H%M%SZ}.sqlite3')
    if out.exists():raise FileExistsError(f'Backup already exists: {out}')
    target=sqlite3.connect(str(out))
    try:connection.backup(target)
    finally:target.close()
    return out
