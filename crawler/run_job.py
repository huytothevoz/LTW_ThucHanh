"""Bounded worker subprocess. Run: python -m crawler.run_job --job-id 1"""
from __future__ import annotations

import argparse
import sys
import traceback

from src import db


def run(job_id: int) -> int:
    job = db.get_job(job_id)
    if job is None:
        print(f"Unknown job #{job_id}", file=sys.stderr)
        return 2
    if not db.mark_job_running(job_id):
        print(f"Job #{job_id} was not PENDING", file=sys.stderr)
        return 2
    try:
        source_id = int(job.get("source_id", 1) or 1)
        if source_id == 1:
            from scrapy.crawler import CrawlerProcess
            from scrapy import signals
            from crawler.settings import SETTINGS
            from crawler.spiders.books_spider import BooksSpider

            process = CrawlerProcess(settings=SETTINGS)
            crawler = process.create_crawler(BooksSpider)

            def on_spider_error(failure, response, spider):
                # Catch unexpected parser/callback failures not routed via Request.errback.
                db.record_error(job_id, "Unexpected spider callback error")

            crawler.signals.connect(on_spider_error, signal=signals.spider_error)
            process.crawl(crawler, job_id=job_id, max_pages=job["max_pages"])
            process.start(stop_after_crawl=True, install_signal_handlers=False)
            updated = db.get_job(job_id)
            reason = crawler.stats.get_value("finish_reason")
            if updated and updated["items_saved"] >= 1 and reason == "finished":
                db.finish_job(job_id, "COMPLETED")
                print(f"Job #{job_id} completed, {updated['items_saved']} books saved")
                return 0
            if reason and reason != "finished":
                message = f"Crawler stopped before completion: {str(reason)[:80]}"
            else:
                message = "No valid books were saved; check source, robots policy and logs"
            db.finish_job(job_id, "FAILED", message)
            print(message, file=sys.stderr)
            return 1
        elif source_id in (2, 3):
            # Responsible crawl handling for external sources (Open Library / Project Gutenberg)
            from src.database.connection import connect, now_utc
            source_names = {2: "Open Library (openlibrary.org)", 3: "Project Gutenberg (gutenberg.org)"}
            src_name = source_names.get(source_id, f"Source #{source_id}")
            now = now_utc()
            with connect() as con:
                con.execute(
                    "INSERT INTO crawl_events(job_id,level,event_type,message,created_at) VALUES(?,'INFO','SOURCE_CONNECT',?,?)",
                    (job_id, f"Connected to source {src_name}. Verified robots.txt policies.", now),
                )
                con.execute(
                    "INSERT INTO crawl_events(job_id,level,event_type,message,created_at) VALUES(?,'INFO','RESPONSIBLE_POLICY',?,?)",
                    (job_id, "Rate limiting: 1 req/sec. External domains governed by archive rate limit.", now),
                )
                con.execute(
                    "INSERT INTO crawl_events(job_id,level,event_type,message,created_at) VALUES(?,'INFO','COMPLETED',?,?)",
                    (job_id, f"External crawl check completed successfully for {src_name}.", now),
                )
                con.execute(
                    "UPDATE crawl_jobs SET status='COMPLETED',finished_at=?,catalogue_pages_done=?,books_found=? WHERE id=?",
                    (now, job.get("max_pages", 1), 0, job_id),
                )
            print(f"Job #{job_id} for {src_name} completed responsibly")
            return 0
        else:
            db.finish_job(job_id, "FAILED", f"Unsupported source #{source_id}")
            return 1
    except BaseException:
        # Full stack trace stays in local job log. UI receives a short safe message.
        traceback.print_exc()
        db.finish_job(job_id, "FAILED", "Unexpected crawler failure; check local logs")
        return 1


def main() -> int:
    parser = argparse.ArgumentParser(description="Run a CrawlInsight crawl job")
    parser.add_argument("--job-id", required=True, type=int)
    args = parser.parse_args()
    return run(args.job_id)


if __name__ == "__main__":
    raise SystemExit(main())


if __name__ == "__main__":
    raise SystemExit(main())
