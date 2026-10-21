"""Single configuration and connection factory. No Flask/Scrapy dependencies."""
from __future__ import annotations
import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
# XAMPP's Apache can serve files from htdocs. Keep live SQLite OUTSIDE
# the document root automatically when the repo resides in htdocs.
if ROOT.parent.name.lower() == 'htdocs':
    DEFAULT_DB = ROOT.parent.parent / 'ltw-th-private-data' / 'crawlinsight.db'
else:
    DEFAULT_DB = ROOT / 'data' / 'crawlinsight.db'
SCHEMA_PATH = ROOT / 'database' / 'schema.sql'
MIGRATIONS_DIR = ROOT / 'database' / 'migrations'


def now_utc() -> str:
    return datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')


def database_path() -> Path:
    configured = os.environ.get('CRAWLINSIGHT_DB_PATH', '').strip()
    return Path(configured).expanduser().resolve() if configured else DEFAULT_DB


def connect() -> sqlite3.Connection:
    path = database_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(str(path), timeout=5)
    con.row_factory = sqlite3.Row
    con.execute('PRAGMA foreign_keys=ON')
    con.execute('PRAGMA busy_timeout=5000')
    return con


def row_dict(row: sqlite3.Row | None) -> dict | None:
    return dict(row) if row is not None else None
