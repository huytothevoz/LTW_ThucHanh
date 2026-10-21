"""SQLite access layer. No HTTP or Scrapy code belongs in this module.

Only this module writes the two tables described by SRS 2.0. Every item
upsert + job counter update takes place in the same SQLite transaction.
"""
from __future__ import annotations

import os
import re
import sqlite3
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path
from urllib.parse import urldefrag, urlsplit

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DB = ROOT / "data" / "crawlinsight.db"
SCHEMA_PATH = ROOT / "database" / "schema.sql"
JOB_FIELDS = (
    "id", "max_pages", "status", "catalogue_pages_done", "books_found",
    "items_saved", "new_books", "existing_books", "error_count", "last_error",
    "created_at", "started_at", "finished_at"
)
TERMINAL_STATUSES = {"COMPLETED", "FAILED"}
ACTIVE_STATUSES = {"PENDING", "RUNNING"}
PRICE_PATTERN = re.compile(r"(?:0|[1-9]\d{0,3})(?:\.\d{1,2})?\Z")


class ActiveJobError(Exception):
    """Raised on an attempt to create a second active crawler job."""


class InvalidBookError(ValueError):
    """Raised when a scraped item violates the agreed item contract."""


def now_utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def database_path() -> Path:
    configured = os.environ.get("CRAWLINSIGHT_DB_PATH", "").strip()
    return Path(configured).expanduser().resolve() if configured else DEFAULT_DB


def connect() -> sqlite3.Connection:
    path = database_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(str(path), timeout=5.0)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA busy_timeout = 5000")
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def init_db() -> None:
    with connect() as connection:
        connection.executescript(SCHEMA_PATH.read_text(encoding="utf-8"))


def row_dict(row: sqlite3.Row | None) -> dict | None:
    return dict(row) if row is not None else None


def create_job(max_pages: int) -> dict:
    # Python bool is an int subclass; type check matters for FR-02.
    if type(max_pages) is not int or max_pages not in (1, 2, 3):
        raise ValueError("max_pages must be an integer from 1 to 3")
    with connect() as connection:
        connection.execute("BEGIN IMMEDIATE")
        active = connection.execute(
            "SELECT id FROM crawl_jobs WHERE status IN ('PENDING','RUNNING') LIMIT 1"
        ).fetchone()
        if active is not None:
            raise ActiveJobError(f"Crawl #{active['id']} is still active")
        cursor = connection.execute(
            "INSERT INTO crawl_jobs(max_pages, status, created_at) VALUES (?, 'PENDING', ?)",
            (max_pages, now_utc()),
        )
        job = connection.execute(
            "SELECT * FROM crawl_jobs WHERE id=?", (cursor.lastrowid,)
        ).fetchone()
        return dict(job)


def get_job(job_id: int) -> dict | None:
    with connect() as connection:
        return row_dict(connection.execute(
            "SELECT * FROM crawl_jobs WHERE id=?", (job_id,)
        ).fetchone())


def mark_job_running(job_id: int) -> bool:
    with connect() as connection:
        result = connection.execute(
            "UPDATE crawl_jobs SET status='RUNNING', started_at=? "
            "WHERE id=? AND status='PENDING'", (now_utc(), job_id)
        )
        return result.rowcount == 1


def finish_job(job_id: int, status: str, reason: str | None = None) -> None:
    if status not in TERMINAL_STATUSES:
        raise ValueError("Invalid terminal status")
    with connect() as connection:
        connection.execute(
            "UPDATE crawl_jobs SET status=?, finished_at=?, "
            "last_error=COALESCE(?, last_error), "
            "error_count=error_count + ? WHERE id=? AND status IN ('PENDING','RUNNING')",
            (status, now_utc(), sanitize_error(reason), 1 if reason else 0, job_id),
        )


def sanitize_error(message: str | None) -> str | None:
    if not message:
        return None
    # Never expose tracebacks/local paths or uncontrolled remote HTML in the UI.
    clean = " ".join(str(message).split())
    return clean[:220]


def record_error(job_id: int, message: str) -> None:
    with connect() as connection:
        connection.execute(
            "UPDATE crawl_jobs SET error_count=error_count+1, last_error=? "
            "WHERE id=? AND status='RUNNING'", (sanitize_error(message), job_id)
        )


def increment_catalogue(job_id: int, discovered: int) -> None:
    if discovered < 0:
        raise ValueError("discovered cannot be negative")
    with connect() as connection:
        connection.execute(
            "UPDATE crawl_jobs SET catalogue_pages_done=catalogue_pages_done+1, "
            "books_found=books_found+? WHERE id=? AND status='RUNNING'",
            (discovered, job_id),
        )


def validate_book(item: dict) -> dict:
    """Validate persisted item, intentionally rejects fabricated defaults."""
    required = ("source_url", "title", "price_pence", "rating", "category", "availability")
    if any(item.get(field) is None for field in required):
        raise InvalidBookError("Missing mandatory book field")
    url, _fragment = urldefrag(str(item["source_url"]))
    parsed = urlsplit(url)
    if parsed.scheme != "https" or parsed.hostname != "books.toscrape.com" or parsed.port is not None:
        raise InvalidBookError("Unapproved book URL")
    if not parsed.path.startswith("/catalogue/") or not parsed.path.endswith("/index.html"):
        raise InvalidBookError("Invalid book detail path")
    if type(item["price_pence"]) is not int or item["price_pence"] < 0:
        raise InvalidBookError("price_pence must be a non-negative integer")
    if type(item["rating"]) is not int or item["rating"] not in range(1, 6):
        raise InvalidBookError("rating must be an integer between 1 and 5")
    result = {"source_url": url, "price_pence": item["price_pence"], "rating": item["rating"]}
    for field in ("title", "category", "availability"):
        value = " ".join(str(item[field]).split())
        if not value:
            raise InvalidBookError(f"Empty {field}")
        result[field] = value[:500]
    for field in ("image_url", "upc"):
        value = item.get(field)
        result[field] = str(value).strip()[:1000] if value else None
    if result["image_url"]:
        image_parts = urlsplit(result["image_url"])
        if image_parts.scheme != "https" or image_parts.hostname != "books.toscrape.com":
            result["image_url"] = None
    return result


def save_book_for_job(job_id: int, book: dict) -> str:
    """Atomically persist a book AND its per-job new/existing counters."""
    values = validate_book(book)
    timestamp = now_utc()
    with connect() as connection:
        connection.execute("BEGIN IMMEDIATE")
        job = connection.execute("SELECT status FROM crawl_jobs WHERE id=?", (job_id,)).fetchone()
        if job is None or job["status"] != "RUNNING":
            raise RuntimeError("Cannot save a book for a non-running job")
        existing = connection.execute(
            "SELECT id FROM books WHERE source_url=?", (values["source_url"],)
        ).fetchone()
        if existing is None:
            connection.execute(
                "INSERT INTO books(source_url,title,price_pence,rating,category,availability,"
                "image_url,upc,first_seen_at,last_seen_at) VALUES (?,?,?,?,?,?,?,?,?,?)",
                (values["source_url"], values["title"], values["price_pence"], values["rating"],
                 values["category"], values["availability"], values["image_url"], values["upc"],
                 timestamp, timestamp),
            )
            kind = "new_books"
        else:
            connection.execute(
                "UPDATE books SET title=?,price_pence=?,rating=?,category=?,availability=?,"
                "image_url=?,upc=?,last_seen_at=? WHERE id=?",
                (values["title"], values["price_pence"], values["rating"], values["category"],
                 values["availability"], values["image_url"], values["upc"], timestamp,
                 existing["id"]),
            )
            kind = "existing_books"
        # kind is chosen exclusively by this function, never from user input.
        connection.execute(
            f"UPDATE crawl_jobs SET items_saved=items_saved+1, {kind}={kind}+1 WHERE id=?",
            (job_id,),
        )
    return "new" if kind == "new_books" else "existing"


def summary() -> dict:
    with connect() as connection:
        total_books = connection.execute("SELECT COUNT(*) FROM books").fetchone()[0]
        completed_jobs = connection.execute(
            "SELECT COUNT(*) FROM crawl_jobs WHERE status='COMPLETED'"
        ).fetchone()[0]
        recent = [dict(row) for row in connection.execute(
            "SELECT id,status,max_pages,items_saved,created_at FROM crawl_jobs ORDER BY id DESC LIMIT 5"
        ).fetchall()]
        last = connection.execute(
            "SELECT id,status,created_at FROM crawl_jobs ORDER BY id DESC LIMIT 1"
        ).fetchone()
        counts = {row["rating"]: row["count"] for row in connection.execute(
            "SELECT rating,COUNT(*) AS count FROM books GROUP BY rating"
        ).fetchall()}
    return {
        "total_books": total_books,
        "completed_jobs": completed_jobs,
        "last_job": row_dict(last),
        "rating_distribution": [
            {"rating": rating, "count": counts.get(rating, 0)} for rating in range(1, 6)
        ],
        "recent_jobs": recent,
    }


def parse_price_filter(value: str | None, key: str) -> int | None:
    if value is None or value == "":
        return None
    if not PRICE_PATTERN.fullmatch(value):
        raise ValueError(f"{key} must be GBP 0–9999.99 with up to 2 decimals")
    try:
        number = int(Decimal(value) * 100)
    except (InvalidOperation, OverflowError):
        raise ValueError(f"Invalid {key}") from None
    if number < 0 or number > 999999:
        raise ValueError(f"{key} is out of range")
    return number


def search_books(q: str = "", min_price: str | None = None,
                 max_price: str | None = None, page: int = 1) -> dict:
    if len(q) > 100:
        raise ValueError("q must be 100 characters or fewer")
    if type(page) is not int or not 1 <= page <= 100000:
        raise ValueError("page must be an integer between 1 and 100000")
    min_pence = parse_price_filter(min_price, "min_price")
    max_pence = parse_price_filter(max_price, "max_price")
    if min_pence is not None and max_pence is not None and min_pence > max_pence:
        raise ValueError("min_price must be less than or equal to max_price")
    conditions = []
    params: list = []
    if q.strip():
        # LIKE backslash escaping: `%`/`_` are literal search terms.
        escaped = q.strip().replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        conditions.append("title LIKE ? ESCAPE '\\' COLLATE NOCASE")
        params.append(f"%{escaped}%")
    if min_pence is not None:
        conditions.append("price_pence >= ?")
        params.append(min_pence)
    if max_pence is not None:
        conditions.append("price_pence <= ?")
        params.append(max_pence)
    where = " WHERE " + " AND ".join(conditions) if conditions else ""
    with connect() as connection:
        total = connection.execute("SELECT COUNT(*) FROM books" + where, params).fetchone()[0]
        rows = connection.execute(
            "SELECT id,title,price_pence,rating,category,availability,image_url,source_url "
            "FROM books" + where + " ORDER BY id DESC LIMIT 12 OFFSET ?",
            [*params, (page - 1) * 12],
        ).fetchall()
    return {
        "items": [dict(row) for row in rows],
        "page": page,
        "page_size": 12,
        "total": total,
        "total_pages": (total + 11) // 12,
    }
