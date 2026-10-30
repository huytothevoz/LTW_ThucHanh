"""Test-only helpers for the retired SQLite demo database."""
from __future__ import annotations
import sqlite3
import os
from pathlib import Path
from src import db


def open_ro(path: Path) -> sqlite3.Connection:
    if not path.is_file():
        raise FileNotFoundError(path)
    connection = sqlite3.connect(path.as_uri() + '?mode=ro', uri=True, timeout=5)
    connection.row_factory = sqlite3.Row
    connection.execute('PRAGMA query_only=ON')
    return connection


def rows_of(connection: sqlite3.Connection, name: str, limit: int = 12) -> list[dict]:
    if not name or name.startswith('sqlite_'):
        raise ValueError('System tables and unknown names are not available')
    row = connection.execute(
        "SELECT name FROM sqlite_master WHERE name=? AND type IN ('table','view')",
        (name,),
    ).fetchone()
    if row is None:
        raise ValueError(f'Unknown table/view: {name}')
    safe_name = '"' + row['name'].replace('"', '""') + '"'
    return [dict(item) for item in connection.execute(f'SELECT * FROM {safe_name} LIMIT ?', (limit,))]


def seed_demo(path: Path) -> Path:
    path = path.resolve()
    if path == db.database_path().resolve():
        raise ValueError('Refusing to insert demo records into the live DB')
    if path.exists():
        raise FileExistsError(f'Demo target already exists: {path}')
    path.parent.mkdir(parents=True, exist_ok=True)
    previous_driver = os.environ.get('DB_CONNECTION')
    previous_path = os.environ.get('CRAWLINSIGHT_DB_PATH')
    os.environ['DB_CONNECTION'] = 'sqlite'
    os.environ['CRAWLINSIGHT_DB_PATH'] = str(path)
    titles = [
        ('[DEMO] A Gentle Introduction to Python', 'Programming', 1750, 4),
        ('[DEMO] Understanding the Web', 'Technology', 2599, 5),
        ('[DEMO] Learning Search Algorithms', 'Science', 1249, 3),
        ('[DEMO] The Art of Databases', 'Technology', 3140, 5),
        ('[DEMO] A Quiet Morning', 'Fiction', 799, 2),
        ('[DEMO] The Ocean Atlas', 'Travel', 3555, 4),
        ('[DEMO] Everyday Statistics', 'Science', 2050, 3),
        ('[DEMO] Coding Together', 'Programming', 2899, 5),
        ('[DEMO] A Winter Letter', 'Fiction', 1595, 4),
        ('[DEMO] Cities and Rivers', 'Travel', 4320, 3),
        ('[DEMO] Data Ethics 101', 'Technology', 1930, 5),
        ('[DEMO] The Small Library', 'Fiction', 1199, 4),
    ]
    try:
        db.init_db()
        with db.connect() as connection:
            connection.execute("UPDATE sources SET name='Books to Scrape — DEMO DATA' WHERE id=1")
        first = db.create_job(1)
        db.mark_job_running(first['id'])
        db.record_catalogue_page(first['id'], 'https://books.toscrape.com/', 1, len(titles))
        for index, (title, category, price, rating) in enumerate(titles, 1):
            db.save_book_for_job(first['id'], {
                'source_url': f'https://books.toscrape.com/catalogue/demo_sample_{index:03d}/index.html',
                'title': title, 'category': category, 'price_pence': price, 'rating': rating,
                'availability': 'In stock', 'image_url': None, 'upc': f'DEMO-{index:03d}',
            })
        db.finish_job(first['id'], 'COMPLETED')
        second = db.create_job(1)
        db.mark_job_running(second['id'])
        db.record_catalogue_page(second['id'], 'https://books.toscrape.com/', 1, 3)
        for index in (1, 2, 3):
            title, category, price, rating = titles[index - 1]
            db.save_book_for_job(second['id'], {
                'source_url': f'https://books.toscrape.com/catalogue/demo_sample_{index:03d}/index.html',
                'title': title, 'category': category, 'price_pence': price + (200 if index == 2 else 0),
                'rating': rating, 'availability': 'In stock', 'image_url': None,
                'upc': f'DEMO-{index:03d}',
            })
        db.finish_job(second['id'], 'COMPLETED')
        with db.connect() as connection:
            if connection.execute('PRAGMA integrity_check').fetchone()[0] != 'ok':
                raise RuntimeError('SQLite demo integrity check failed')
    finally:
        if previous_driver is None:
            os.environ.pop('DB_CONNECTION', None)
        else:
            os.environ['DB_CONNECTION'] = previous_driver
        if previous_path is None:
            os.environ.pop('CRAWLINSIGHT_DB_PATH', None)
        else:
            os.environ['CRAWLINSIGHT_DB_PATH'] = previous_path
    return path
