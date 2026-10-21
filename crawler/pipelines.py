"""Scrapy item pipeline: contract validation and atomic upsert + job counters."""
from __future__ import annotations

from scrapy.exceptions import DropItem

from src import db


class SQLiteBookPipeline:
    def process_item(self, item, spider):
        try:
            outcome = db.save_book_for_job(spider.job_id, dict(item))
            spider.logger.debug("Saved %s book: %s", outcome, item.get("source_url"))
            return item
        except db.InvalidBookError as exc:
            db.record_error(spider.job_id, f"Invalid extracted book: {exc}")
            raise DropItem(str(exc)) from exc
        except Exception:
            db.record_error(spider.job_id, "Database error while saving a book")
            # Fail loudly if database writes are unsafe instead of silently continuing.
            raise
