"""Pure parsing helpers always run; HtmlResponse test runs with Scrapy installed."""
from pathlib import Path

import pytest

from crawler.parser import ParseError, normalise_url, parse_availability, parse_price, parse_rating


@pytest.mark.parametrize("price,pence", [("£12.34", 1234), (" £0.99 ", 99), ("£51.77", 5177)])
def test_price_uses_decimal_pence(price, pence):
    assert parse_price(price) == pence


def test_rating_five_point_scale():
    assert parse_rating(["star-rating", "Four"]) == 4
    with pytest.raises(ParseError):
        parse_rating(["star-rating", "Six"])


def test_availability_normalized():
    assert parse_availability(" In stock (22 available) ") == "In stock"
    assert parse_availability("Out of stock") == "Out of stock"


def test_source_allowlist():
    assert normalise_url("https://books.toscrape.com/catalogue/s_1/index.html#intro") == \
        "https://books.toscrape.com/catalogue/s_1/index.html"
    assert normalise_url("https://other.example/catalogue/s_1/index.html") is None
    assert normalise_url("http://books.toscrape.com/catalogue/s_1/index.html") is None


def test_html_detail_fixture():
    scrapy = pytest.importorskip("scrapy")
    from scrapy.http import HtmlResponse, Request
    from crawler.parser import parse_book
    path = Path(__file__).parent / "fixtures" / "book_detail.html"
    url = "https://books.toscrape.com/catalogue/sample_book_9/index.html"
    response = HtmlResponse(url=url, body=path.read_bytes(), encoding="utf-8", request=Request(url))
    item = parse_book(response)
    assert item["title"] == "A Fixture Book"
    assert item["price_pence"] == 1234
    assert item["rating"] == 4
    assert item["category"] == "Travel"
    assert item["availability"] == "In stock"
    assert item["upc"] == "FIXTURE-001"
    assert item["image_url"].startswith("https://books.toscrape.com/media/")


def test_html_missing_price_rejected():
    scrapy = pytest.importorskip("scrapy")
    from scrapy.http import HtmlResponse, Request
    from crawler.parser import parse_book
    url = "https://books.toscrape.com/catalogue/sample_book_9/index.html"
    html = '<html><div class="product_main"><h1>Title</h1><p class="star-rating One"></p>' \
           '<p class="availability">In stock</p></div><ul class="breadcrumb"><li>Home</li>' \
           '<li><a>Travel</a></li><li>Book</li></ul></html>'
    response = HtmlResponse(url=url, body=html.encode(), encoding="utf-8", request=Request(url))
    with pytest.raises(ParseError):
        parse_book(response)
