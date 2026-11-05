"""Offline tests for Open Library and Project Gutenberg crawlers and parsers."""
from pathlib import Path
import pytest

from crawler.parser import (
    normalise_openlibrary_url,
    parse_openlibrary_book,
    normalise_gutenberg_url,
    parse_gutenberg_book,
    ParseError,
)
from crawler.middlewares import is_approved_request_url
from src.database.books import validate_book, InvalidBookError

scrapy = pytest.importorskip("scrapy")
from scrapy.http import HtmlResponse, Request
from crawler.spiders.openlibrary_spider import OpenLibrarySpider
from crawler.spiders.gutenberg_spider import GutenbergSpider


FIXTURES = Path(__file__).parent / "fixtures"


# --- Open Library Parser Tests ---

def test_normalise_openlibrary_url():
    assert normalise_openlibrary_url("https://openlibrary.org/works/OL17930368W/Atomic_Habits?edition=key%3A/books/OL27918581M#section") == \
        "https://openlibrary.org/works/OL17930368W"
    assert normalise_openlibrary_url("https://openlibrary.org/authors/OL734567A") is None
    assert normalise_openlibrary_url("http://openlibrary.org/works/OL123W") is None
    assert normalise_openlibrary_url("https://malicious.org/works/OL123W") is None


def test_parse_openlibrary_book_fixture():
    url = "https://openlibrary.org/works/OL17930368W"
    html = (FIXTURES / "openlibrary_detail.html").read_bytes()
    response = HtmlResponse(url=url, body=html, encoding="utf-8", request=Request(url))
    item = parse_openlibrary_book(response)

    assert "Atomic Habits" in item["title"]
    assert item["source_url"] == "https://openlibrary.org/works/OL17930368W"
    assert item["price_pence"] > 0
    assert 1 <= item["rating"] <= 5
    assert item["availability"] == "In stock"
    assert item["upc"] == "OL17930368W"
    assert item["image_url"] == "https://covers.openlibrary.org/b/id/11646973-L.jpg"
    assert item["category"] == "Self-help"


# --- Project Gutenberg Parser Tests ---

def test_normalise_gutenberg_url():
    assert normalise_gutenberg_url("https://www.gutenberg.org/ebooks/1342#download") == \
        "https://www.gutenberg.org/ebooks/1342"
    assert normalise_gutenberg_url("https://gutenberg.org/ebooks/84") == \
        "https://www.gutenberg.org/ebooks/84"
    assert normalise_gutenberg_url("https://www.gutenberg.org/browse/scores/top") is None
    assert normalise_gutenberg_url("http://www.gutenberg.org/ebooks/1342") is None


def test_parse_gutenberg_book_fixture():
    url = "https://www.gutenberg.org/ebooks/1342"
    html = (FIXTURES / "gutenberg_detail.html").read_bytes()
    response = HtmlResponse(url=url, body=html, encoding="utf-8", request=Request(url))
    item = parse_gutenberg_book(response)

    assert item["title"] == "Pride and Prejudice"
    assert item["source_url"] == "https://www.gutenberg.org/ebooks/1342"
    assert item["price_pence"] > 0
    assert 1 <= item["rating"] <= 5
    assert item["availability"] == "In stock"
    assert item["upc"] == "1342"
    assert item["image_url"] == "https://www.gutenberg.org/cache/epub/1342/pg1342.cover.medium.jpg"
    assert "Fiction" in item["category"] or item["category"] == "England -- Fiction"


# --- Validation Tests ---

def test_validate_book_multi_source():
    # Source 1: Books to Scrape
    b1 = {
        "source_url": "https://books.toscrape.com/catalogue/a-light-in-the-attic_1000/index.html",
        "title": "A Light in the Attic",
        "price_pence": 5177,
        "rating": 3,
        "category": "Poetry",
        "availability": "In stock",
        "image_url": "https://books.toscrape.com/media/cache/test.jpg",
        "upc": "A1B2C3",
    }
    assert validate_book(b1)["source_url"] == b1["source_url"]

    # Source 2: Open Library
    b2 = {
        "source_url": "https://openlibrary.org/works/OL17930368W",
        "title": "Atomic Habits",
        "price_pence": 0,
        "rating": 4,
        "category": "Self-help",
        "availability": "In stock",
        "image_url": "https://covers.openlibrary.org/b/id/11646973-L.jpg",
        "upc": "OL17930368W",
    }
    assert validate_book(b2)["source_url"] == b2["source_url"]

    # Source 3: Project Gutenberg
    b3 = {
        "source_url": "https://www.gutenberg.org/ebooks/1342",
        "title": "Pride and Prejudice",
        "price_pence": 0,
        "rating": 5,
        "category": "Classics",
        "availability": "In stock",
        "image_url": "https://www.gutenberg.org/cache/epub/1342/pg1342.cover.medium.jpg",
        "upc": "1342",
    }
    assert validate_book(b3)["source_url"] == b3["source_url"]

    # Rejected URLs
    with pytest.raises(InvalidBookError):
        validate_book({**b1, "source_url": "https://unknown.com/book/1"})


# --- Spider Offline Scheduling Tests ---

def test_openlibrary_spider_catalogue(monkeypatch):
    records = []
    monkeypatch.setattr("crawler.spiders.openlibrary_spider.db.record_catalogue_page",
                        lambda job_id, url, page_number, count: records.append((job_id, url, page_number, count)))
    spider = OpenLibrarySpider(job_id=99, max_pages=2)
    url = "https://openlibrary.org/trending/daily"
    html = (FIXTURES / "openlibrary_catalogue.html").read_bytes()
    response = HtmlResponse(url=url, body=html, encoding="utf-8", request=Request(url))

    emitted = list(spider.parse(response))
    details = [req for req in emitted if req.meta.get("kind") == "detail"]
    catalogues = [req for req in emitted if req.meta.get("kind") == "catalogue"]

    assert len(records) == 1
    assert records[0] == (99, "https://openlibrary.org/trending/daily?page=1", 1, 2)
    assert len(details) == 2
    assert len(catalogues) == 1
    assert catalogues[0].url == "https://openlibrary.org/trending/daily?page=2"


def test_gutenberg_spider_catalogue(monkeypatch):
    records = []
    monkeypatch.setattr("crawler.spiders.gutenberg_spider.db.record_catalogue_page",
                        lambda job_id, url, page_number, count: records.append((job_id, url, page_number, count)))
    spider = GutenbergSpider(job_id=100, max_pages=1)
    url = "https://www.gutenberg.org/browse/scores/top"
    html = (FIXTURES / "gutenberg_catalogue.html").read_bytes()
    response = HtmlResponse(url=url, body=html, encoding="utf-8", request=Request(url))

    emitted = list(spider.parse(response))
    details = [req for req in emitted if req.meta.get("kind") == "detail"]

    assert len(records) == 1
    assert records[0] == (100, "https://www.gutenberg.org/browse/scores/top?page=1", 1, 3)
    assert len(details) == 3


def test_external_spiders_resume_at_requested_page():
    openlibrary = OpenLibrarySpider(job_id=102, max_pages=2, start_page=4)
    assert next(openlibrary.start_requests()).url == "https://openlibrary.org/trending/daily?page=4"
    assert GutenbergSpider(job_id=103, max_pages=2, start_page=4).start_urls == [
        "https://www.gutenberg.org/browse/scores/top?page=4"
    ]


def test_middleware_allows_approved_sources():
    assert is_approved_request_url("https://books.toscrape.com/catalogue/page-1.html") is True
    assert is_approved_request_url("https://openlibrary.org/trending/daily") is True
    assert is_approved_request_url("https://www.gutenberg.org/browse/scores/top") is True
    assert is_approved_request_url("https://evil.com/phishing") is False
    assert is_approved_request_url("http://books.toscrape.com/") is False



def test_openlibrary_spider_resilient_snapshot(monkeypatch):
    records = []
    monkeypatch.setattr("crawler.spiders.openlibrary_spider.db.record_catalogue_page",
                        lambda job_id, url, page_number, count: records.append((job_id, url, page_number, count)))
    spider = OpenLibrarySpider(job_id=101, max_pages=2)
    items = list(spider.yield_archive_snapshot(page_number=1))
    assert len(items) == 40
    assert len(records) == 2
    assert records[0][2] == 1
    assert records[1][2] == 2
    for item in items:
        assert item["price_pence"] > 0
        assert 1 <= item["rating"] <= 5
        assert item["source_url"].startswith("https://openlibrary.org/works/")
        assert item["image_url"].startswith("https://covers.openlibrary.org/b/id/")
