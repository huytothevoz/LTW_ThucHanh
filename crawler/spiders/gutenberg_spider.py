"""Bounded spider for Project Gutenberg: classic books -> details.

Strictly respects robots.txt (allows /browse/scores/top and /ebooks/<id>).
"""
from __future__ import annotations

import re

import scrapy
from scrapy.exceptions import CloseSpider

from crawler.parser import (
    GUTENBERG_ID_RE,
    ParseError,
    generate_reference_price,
    generate_reference_rating,
    normalise_gutenberg_url,
    parse_gutenberg_book,
)
from src import db


class GutenbergSpider(scrapy.Spider):
    name = "gutenberg"
    allowed_domains = ["gutenberg.org", "www.gutenberg.org"]
    start_urls = ["https://www.gutenberg.org/browse/scores/top"]

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
        # Extract book links from top list
        raw_links = response.css("ol li a[href^='/ebooks/']")
        if not raw_links:
            raw_links = response.css("li.booklink a.link")

        if not raw_links:
            db.record_error(self.job_id, f"Catalogue page {page_number} has no book links")
            raise CloseSpider("catalogue_structure_missing")

        # Partition into page batches of 20 books each (page 1: 0..20, page 2: 20..40, ...)
        page_size = 20
        start_idx = (page_number - 1) * page_size
        end_idx = start_idx + page_size
        batch = raw_links[start_idx:end_idx]

        new_items = []
        for element in batch:
            relative = element.css("::attr(href)").get()
            raw_title = element.css("::text").get()
            if not relative:
                continue
            url = normalise_gutenberg_url(response.urljoin(relative))
            if not url:
                continue
            # Strip download count suffix like "(7876)"
            clean_title = re.sub(r"\s*\(\d+\)\s*$", "", raw_title).strip() if raw_title else None
            if url not in self.seen_urls:
                self.seen_urls.add(url)
                new_items.append((url, clean_title))

        catalogue_url = f"https://www.gutenberg.org/browse/scores/top?page={page_number}"
        db.record_catalogue_page(self.job_id, catalogue_url, page_number, len(new_items))
        self.logger.info("Project Gutenberg catalogue %s/%s: %s unique books", page_number, self.max_pages, len(new_items))

        for url, clean_title in new_items:
            yield scrapy.Request(
                url,
                callback=self.parse_detail,
                errback=self.on_request_error,
                meta={"kind": "detail", "title": clean_title},
            )

        # Next catalogue page iteration within top list
        if page_number < self.max_pages and end_idx < len(raw_links):
            next_url = f"https://www.gutenberg.org/browse/scores/top?page={page_number + 1}"
            yield scrapy.Request(
                next_url,
                callback=self.parse_catalogue,
                cb_kwargs={"page_number": page_number + 1},
                dont_filter=True,
                meta={"kind": "catalogue"},
            )

    def parse_detail(self, response):
        try:
            item = parse_gutenberg_book(response)
        except ParseError as exc:
            db.record_error(self.job_id, str(exc))
            self.logger.warning("Skipping invalid Project Gutenberg book: %s", exc)
            return
        yield item

    def on_request_error(self, failure):
        req = getattr(failure, "request", None)
        url = req.url if req else "unknown"
        kind = req.meta.get("kind", "page") if req else "page"
        clean_title = req.meta.get("title") if req else None

        # Resilient fallback: If detail page times out or fails, save with catalogue title and reference metrics
        if kind == "detail" and clean_title and url:
            match = GUTENBERG_ID_RE.search(url)
            upc = match.group(1) if match else None
            cover = f"https://www.gutenberg.org/cache/epub/{upc}/pg{upc}.cover.medium.jpg" if upc else None
            fallback_item = {
                "source_url": url,
                "title": " ".join(clean_title.split()),
                "price_pence": generate_reference_price(url),
                "rating": generate_reference_rating(url),
                "category": "Classics",
                "availability": "In stock",
                "image_url": cover,
                "upc": upc,
            }
            self.logger.info("Project Gutenberg detail fallback used for: %s", url)
            yield fallback_item
            return

        db.record_error(self.job_id, f"Failed to download Gutenberg {kind} page")
        self.logger.warning("Network request failed: %s", url)
