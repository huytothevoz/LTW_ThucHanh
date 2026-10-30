"""One-source, bounded spider: listing -> next page -> book details.

No arbitrary user-provided URL or ecommerce sites other than Books to Scrape.
"""
from __future__ import annotations

import scrapy
from scrapy.exceptions import CloseSpider

from crawler.parser import ParseError, normalise_url, parse_book
from src import db


class BooksSpider(scrapy.Spider):
    name = "books"
    allowed_domains = ["books.toscrape.com"]
    start_urls = ["https://books.toscrape.com/"]

    def __init__(self, job_id: int, max_pages: int = 1, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.job_id = int(job_id)
        self.max_pages = int(max_pages)
        if self.max_pages not in (1, 2, 3, 4, 5):
            raise ValueError("max_pages outside SRS scope")
        self.seen_urls: set[str] = set()

    def parse(self, response):
        return self.parse_catalogue(response, page_number=1)

    def parse_catalogue(self, response, page_number: int):
        cards = response.css("article.product_pod")
        if not cards:
            db.record_error(self.job_id, f"Catalogue page {page_number} has no book cards")
            raise CloseSpider("catalogue_structure_missing")
        new_urls = []
        for card in cards:
            relative = card.css("h3 a::attr(href)").get()
            if not relative:
                db.record_error(self.job_id, "Catalogue card is missing a detail link")
                continue
            url = normalise_url(response.urljoin(relative))
            if not url:
                db.record_error(self.job_id, "A catalogue link was rejected by the URL allowlist")
                continue
            if url not in self.seen_urls:
                self.seen_urls.add(url)
                new_urls.append(url)
        # Counter records unique *scheduled* book detail URLs, not HTTP requests.
        db.record_catalogue_page(self.job_id, response.url, page_number, len(new_urls))
        self.logger.info("Catalogue %s/%s: %s unique books", page_number, self.max_pages, len(new_urls))
        for url in new_urls:
            yield scrapy.Request(
                url, callback=self.parse_detail, errback=self.on_request_error,
                meta={"kind": "detail"}
            )
        if page_number < self.max_pages:
            next_href = response.css("li.next a::attr(href)").get()
            if not next_href:
                db.record_error(self.job_id, "Next catalogue link is missing")
                return
            next_url = response.urljoin(next_href)
            from urllib.parse import urlsplit
            parsed = urlsplit(next_url)
            if (parsed.scheme != "https" or parsed.hostname != "books.toscrape.com"
                    or not parsed.path.startswith("/catalogue/page-")
                    or not parsed.path.endswith(".html")):
                db.record_error(self.job_id, "Next catalogue link was rejected")
                return
            yield scrapy.Request(
                next_url, callback=self.parse_catalogue,
                cb_kwargs={"page_number": page_number + 1},
                errback=self.on_request_error,
                meta={"kind": "catalogue"},
            )

    def parse_detail(self, response):
        try:
            item = parse_book(response)
        except ParseError as exc:
            db.record_error(self.job_id, str(exc))
            self.logger.warning("Skipping invalid book: %s", exc)
            return
        yield item

    def on_request_error(self, failure):
        url = failure.request.url
        # Avoid injecting untrusted URLs into a public-facing message.
        kind = failure.request.meta.get("kind", "page")
        db.record_error(self.job_id, f"Failed to download {kind} page")
        self.logger.warning("Network request failed: %s", url)
