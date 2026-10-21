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
