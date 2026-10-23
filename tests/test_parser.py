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


def test_html_missing_title_rejected():
    scrapy = pytest.importorskip("scrapy")
    from scrapy.http import HtmlResponse, Request
    from crawler.parser import parse_book
    url = "https://books.toscrape.com/catalogue/sample_book_9/index.html"
    html = '<html><div class="product_main"><p class="price_color">£10.00</p><p class="star-rating One"></p>' \
           '<p class="availability">In stock</p></div><ul class="breadcrumb"><li>Home</li>' \
           '<li><a>Travel</a></li><li>Book</li></ul></html>'
    response = HtmlResponse(url=url, body=html.encode(), encoding="utf-8", request=Request(url))
    with pytest.raises(ParseError, match="Book title is missing"):
        parse_book(response)


def test_html_missing_category_rejected():
    scrapy = pytest.importorskip("scrapy")
    from scrapy.http import HtmlResponse, Request
    from crawler.parser import parse_book
    url = "https://books.toscrape.com/catalogue/sample_book_9/index.html"
    html = '<html><div class="product_main"><h1>A Valid Title</h1><p class="price_color">£10.00</p>' \
           '<p class="star-rating One"></p><p class="availability">In stock</p></div></html>'
    response = HtmlResponse(url=url, body=html.encode(), encoding="utf-8", request=Request(url))
    with pytest.raises(ParseError, match="Book category is missing"):
        parse_book(response)


def test_html_insecure_image_url_sanitized():
    scrapy = pytest.importorskip("scrapy")
    from scrapy.http import HtmlResponse, Request
    from crawler.parser import parse_book
    url = "https://books.toscrape.com/catalogue/sample_book_9/index.html"
    html = '<html><div class="product_main"><h1>A Valid Title</h1><p class="price_color">£10.00</p>' \
           '<p class="star-rating Three"></p><p class="availability">In stock</p></div>' \
           '<ul class="breadcrumb"><li>Home</li><li><a>Travel</a></li><li>Book</li></ul>' \
           '<div class="item active"><img src="http://books.toscrape.com/media/book.jpg"/></div></html>'
    response = HtmlResponse(url=url, body=html.encode(), encoding="utf-8", request=Request(url))
    item = parse_book(response)
    assert item["image_url"] is None


@pytest.mark.parametrize("invalid_price", ["", "12.34", "$12.34", "free", "£-10", "£abc", None])
def test_price_invalid_inputs(invalid_price):
    with pytest.raises(ParseError):
        parse_price(invalid_price)


@pytest.mark.parametrize("invalid_rating", [None, [], ["star-rating"], ["star-rating", "Zero"], ["Six"]])
def test_rating_invalid_inputs(invalid_rating):
    with pytest.raises(ParseError):
        parse_rating(invalid_rating)


@pytest.mark.parametrize("invalid_url", [
    "https://books.toscrape.com:8080/catalogue/book/index.html",
    "https://user:pass@books.toscrape.com/catalogue/book/index.html",
    "https://books.toscrape.com/about/index.html",
    "https://books.toscrape.com/catalogue/book/view.php",
    "javascript:alert(1)",
])
def test_url_normalization_edge_cases(invalid_url):
    assert normalise_url(invalid_url) is None

