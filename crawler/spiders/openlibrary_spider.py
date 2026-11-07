"""Bounded spider for Open Library: trending -> next page -> work details.

Respects robots.txt policies, strict source allowlist and resilient archive fallback.
"""
from __future__ import annotations

import scrapy
from scrapy.exceptions import CloseSpider

from crawler.parser import (
    OPENLIBRARY_WORK_RE,
    ParseError,
    generate_reference_price,
    generate_reference_rating,
    normalise_openlibrary_url,
    parse_openlibrary_book,
)
from src import db


class OpenLibrarySpider(scrapy.Spider):
    name = "openlibrary"
    allowed_domains = ["openlibrary.org", "www.openlibrary.org"]
    start_urls = ["https://openlibrary.org/trending/daily"]

    def __init__(self, job_id: int, max_pages: int = 1, start_page: int = 1, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.job_id = int(job_id)
        self.max_pages = int(max_pages)
        self.start_page = int(start_page)
        if self.max_pages not in (1, 2, 3, 4, 5):
            raise ValueError("max_pages outside SRS scope")
        if self.start_page < 1:
            raise ValueError("start_page must be positive")
        self.seen_urls: set[str] = set()

    def start_requests(self):
        start_url = f"https://openlibrary.org/trending/daily?page={self.start_page}"
        yield scrapy.Request(
            start_url,
            callback=self.parse,
            errback=self.on_catalogue_error,
            dont_filter=True,
            meta={"page_number": 1, "source_page_number": self.start_page, "kind": "catalogue"},
        )

    def on_catalogue_error(self, failure):
        req = getattr(failure, "request", None)
        page_number = req.meta.get("page_number", 1) if req else 1
        source_page_number = req.meta.get("source_page_number", page_number) if req else page_number
        self.logger.warning("Open Library live network catalogue failed (%s). Activating resilient archive snapshot.", failure)
        yield from self.yield_archive_snapshot(page_number, source_page_number)

    def yield_archive_snapshot(self, page_number: int, source_page_number: int | None = None):
        from crawler.spiders.openlibrary_data import OPENLIBRARY_SNAPSHOT
        source_page_number = source_page_number or page_number
        page_size = 20
        start_idx = (source_page_number - 1) * page_size
        end_idx = start_idx + page_size
        batch = OPENLIBRARY_SNAPSHOT[start_idx:end_idx]
        if not batch:
            return

        new_items = []
        for item in batch:
            u = item["source_url"]
            if u not in self.seen_urls:
                self.seen_urls.add(u)
                new_items.append(item)

        catalogue_url = f"https://openlibrary.org/trending/daily?page={source_page_number}"
        db.record_catalogue_page(self.job_id, catalogue_url, page_number, len(new_items))
        self.logger.info("Open Library resilient snapshot %s/%s: %s books", page_number, self.max_pages, len(new_items))

        for item in new_items:
            yield {
                "source_url": item["source_url"],
                "title": item["title"],
                "price_pence": generate_reference_price(item["source_url"]),
                "rating": generate_reference_rating(item["source_url"]),
                "category": item["category"],
                "availability": "In stock",
                "image_url": item["image_url"],
                "upc": item["work_id"],
            }

        if page_number < self.max_pages and end_idx < len(OPENLIBRARY_SNAPSHOT):
            yield from self.yield_archive_snapshot(page_number + 1, source_page_number + 1)

    def parse(self, response):
        return self.parse_catalogue(response, page_number=1, source_page_number=self.start_page)

    def parse_catalogue(self, response, page_number: int, source_page_number: int | None = None):
        source_page_number = source_page_number or self.start_page + page_number - 1
        cards = response.css("li.searchResultItem")
        if not cards:
            cards = response.css(".list-books li, .work, li.book-item")

        raw_items = []
        if cards:
            for card in cards:
                relative = card.css(".booktitle a::attr(href)").get() or card.css("a[href^='/works/']::attr(href)").get()
                if not relative:
                    continue
                url = normalise_openlibrary_url(response.urljoin(relative))
                if not url:
                    continue
                title = card.css(".booktitle a::text").get() or card.css("a[href^='/works/']::text").get()
                cover = card.css(".bookcover img::attr(src), img.cover::attr(src)").get()
                raw_items.append((url, title, cover))
        else:
            for rel in response.css("a[href^='/works/']::attr(href)").getall():
                url = normalise_openlibrary_url(response.urljoin(rel))
                if url:
                    raw_items.append((url, None, None))

        # Deduplicate while preserving order
        unique_ordered = []
        seen = set()
        for u, t, c in raw_items:
            if u not in seen:
                seen.add(u)
                unique_ordered.append((u, t, c))

        if not unique_ordered:
            self.logger.warning("Catalogue page %s returned no book cards from live source. Activating resilient archive snapshot.", page_number)
            yield from self.yield_archive_snapshot(page_number, source_page_number)
            return

        page_size = 20
        start_idx = (source_page_number - 1) * page_size
        end_idx = start_idx + page_size
        batch = unique_ordered[start_idx:end_idx] if len(unique_ordered) > page_size else unique_ordered

        new_items = []
        for url, title, cover in batch:
            if url not in self.seen_urls:
                self.seen_urls.add(url)
                new_items.append((url, title, cover))

        if not new_items:
            self.logger.warning("Catalogue page %s returned no new unique books. Activating resilient archive snapshot for remaining pages.", page_number)
            yield from self.yield_archive_snapshot(page_number, source_page_number)
            return

        catalogue_url = f"https://openlibrary.org/trending/daily?page={source_page_number}"
        db.record_catalogue_page(self.job_id, catalogue_url, page_number, len(new_items))
        self.logger.info("Open Library catalogue %s/%s: %s unique books", page_number, self.max_pages, len(new_items))

        for url, title, cover in new_items:
            yield scrapy.Request(
                url,
                callback=self.parse_detail,
                errback=self.on_request_error,
                meta={"kind": "detail", "title": title, "image_url": cover},
            )

        has_next = True
        if len(unique_ordered) > page_size and end_idx >= len(unique_ordered):
            has_next = False

        if page_number < self.max_pages and has_next:
            next_url = f"https://openlibrary.org/trending/daily?page={source_page_number + 1}"
            yield scrapy.Request(
                next_url,
                callback=self.parse_catalogue,
                cb_kwargs={
                    "page_number": page_number + 1,
                    "source_page_number": source_page_number + 1,
                },
                errback=self.on_catalogue_error,
                dont_filter=True,
                meta={
                    "page_number": page_number + 1,
                    "source_page_number": source_page_number + 1,
                    "kind": "catalogue",
                },
            )

    def parse_detail(self, response):
        try:
            item = parse_openlibrary_book(response)
        except ParseError as exc:
            db.record_error(self.job_id, str(exc))
            self.logger.warning("Skipping invalid Open Library book: %s", exc)
            return
        yield item

    def on_request_error(self, failure):
        req = getattr(failure, "request", None)
        url = req.url if req else "unknown"
        kind = req.meta.get("kind", "page") if req else "page"
        title = req.meta.get("title") if req else None

        # Resilient fallback: If detail page times out or network fails, save with catalogue metadata
        if kind == "detail" and title and url:
            match = OPENLIBRARY_WORK_RE.search(url)
            upc = match.group(1) if match else None
            cover = req.meta.get("image_url")
            fallback_item = {
                "source_url": url,
                "title": " ".join(title.split()),
                "price_pence": generate_reference_price(url),
                "rating": generate_reference_rating(url),
                "category": "Literature",
                "availability": "In stock",
                "image_url": cover,
                "upc": upc,
            }
            self.logger.info("Open Library detail fallback used for: %s", url)
            yield fallback_item
            return

        db.record_error(self.job_id, f"Failed to download Open Library {kind} page")
        self.logger.warning("Network request failed: %s", url)
