"""Shared MySQL runtime connection and explicit SQLite legacy/test support."""
from __future__ import annotations
import os
import re
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pymysql
from pymysql.cursors import DictCursor
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[2]
load_dotenv(ROOT / '.env', override=False)
if ROOT.parent.name.lower() == 'htdocs':
    DEFAULT_DB = ROOT.parent.parent / 'ltw-th-private-data' / 'crawlinsight.db'
else:
    DEFAULT_DB = ROOT / 'data' / 'crawlinsight.db'
SCHEMA_PATH = ROOT / 'database' / 'schema.sql'
MYSQL_SCHEMA_PATH = ROOT / 'database' / 'mysql_schema.sql'
MIGRATIONS_DIR = ROOT / 'database' / 'migrations'


class HybridRow(dict):
    """Dict-style row that also preserves SQLite's numeric column access."""

    def __getitem__(self, key: Any) -> Any:
        if isinstance(key, int):
            return tuple(self.values())[key]
        return super().__getitem__(key)


class MySQLCursor:
    def __init__(self, cursor: Any):
        self._cursor = cursor

    @property
    def rowcount(self) -> int:
        return self._cursor.rowcount

    @property
    def lastrowid(self) -> int | None:
        return self._cursor.lastrowid

    def fetchone(self) -> HybridRow | None:
        row = self._cursor.fetchone()
        return HybridRow(row) if row is not None else None

    def fetchall(self) -> list[HybridRow]:
        return [HybridRow(row) for row in self._cursor.fetchall()]

    def __iter__(self):
        for row in self._cursor:
            yield HybridRow(row)


class MySQLConnection:
    def __init__(self, connection: Any):
        self._connection = connection

    @staticmethod
    def _sql(statement: str) -> str:
        statement = statement.replace('INSERT OR IGNORE INTO', 'INSERT IGNORE INTO')
        statement = statement.replace('COLLATE NOCASE', '')
        if statement.strip().upper() == 'BEGIN IMMEDIATE':
            return 'START TRANSACTION'
        statement = statement.replace('last_insert_rowid()', 'LAST_INSERT_ID()')
        statement = statement.replace('?', '%s')
        return re.sub(r'\bIS\s+%s\b', '<=> %s', statement, flags=re.IGNORECASE)

    def execute(self, statement: str, parameters: Any = ()) -> MySQLCursor:
        cursor = self._connection.cursor()
        cursor.execute(self._sql(statement), parameters)
        return MySQLCursor(cursor)

    def commit(self) -> None:
        self._connection.commit()

    def rollback(self) -> None:
        self._connection.rollback()

    def close(self) -> None:
        self._connection.close()

    def __enter__(self) -> MySQLConnection:
        return self

    def __exit__(self, exception_type: Any, exception: Any, traceback: Any) -> None:
        try:
            if exception_type is None:
                self.commit()
            else:
                self.rollback()
        finally:
            self.close()


def now_utc() -> str:
    return datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')


def database_path() -> Path:
    configured = os.environ.get('CRAWLINSIGHT_DB_PATH', '').strip()
    return Path(configured).expanduser().resolve() if configured else DEFAULT_DB


def database_driver() -> str:
    return os.environ.get('DB_CONNECTION', 'mysql').strip().lower()


def connect() -> sqlite3.Connection | MySQLConnection:
    if database_driver() == 'sqlite':
        path = database_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        con = sqlite3.connect(str(path), timeout=5)
        con.row_factory = sqlite3.Row
        con.execute('PRAGMA foreign_keys=ON')
        con.execute('PRAGMA busy_timeout=5000')
        return con
    if database_driver() != 'mysql':
        raise ValueError('DB_CONNECTION must be mysql or sqlite')

    database = os.environ.get('DB_DATABASE', 'crawlinsight').strip()
    if not re.fullmatch(r'[A-Za-z0-9_]+', database):
        raise ValueError('DB_DATABASE may contain only letters, numbers, and underscores')
    connection = pymysql.connect(
        host=os.environ.get('DB_HOST', '127.0.0.1'),
        port=int(os.environ.get('DB_PORT', '3308')),
        user=os.environ.get('DB_USERNAME', 'root'),
        password=os.environ.get('DB_PASSWORD', ''),
        database=database,
        charset='utf8mb4',
        cursorclass=DictCursor,
        autocommit=False,
        connect_timeout=5,
    )
    return MySQLConnection(connection)


def row_dict(row: sqlite3.Row | dict | None) -> dict | None:
    return dict(row) if row is not None else None
