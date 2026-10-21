"""Small, testable HTML-extraction helpers for Books to Scrape."""
from __future__ import annotations

import re
from decimal import Decimal, InvalidOperation
from urllib.parse import urldefrag, urlsplit

RATINGS = {"One": 1, "Two": 2, "Three": 3, "Four": 4, "Five": 5}
PRICE_RE = re.compile(r"£\s*(\d+(?:\.\d{1,2})?)")


class ParseError(ValueError):
    """HTML response is missing required details or contains invalid data."""


def normalise_url(url: str) -> str | None:
    url, _ = urldefrag(url)
    parts = urlsplit(url)
    if parts.scheme != "https" or parts.hostname != "books.toscrape.com":
        return None
    if parts.username or parts.password or parts.port is not None:
        return None
    if not parts.path.startswith("/catalogue/") or not parts.path.endswith("/index.html"):
        return None
    return url


def parse_price(price_text: str | None) -> int:
    match = PRICE_RE.search(price_text or "")
    if not match:
        raise ParseError("Book price is missing or invalid")
    try:
        return int(Decimal(match.group(1)) * 100)
    except (InvalidOperation, ValueError):
        raise ParseError("Book price cannot be parsed") from None


def parse_rating(classes: list[str] | None) -> int:
    for cls in classes or []:
        if cls in RATINGS:
            return RATINGS[cls]
    raise ParseError("Book rating is missing or invalid")


def parse_availability(text: str) -> str:
    clean = " ".join(text.split())
    if not clean:
        raise ParseError("Book availability is missing")
    if "in stock" in clean.casefold():
        return "In stock"
    if "out of stock" in clean.casefold():
        return "Out of stock"
    return clean


def parse_book(response) -> dict:
    """Scrapy HtmlResponse in, plain dict out; deliberately no fallback fixtures."""
    url = normalise_url(response.url)
    if not url:
        raise ParseError("Book detail is outside approved source")
    title = response.css("div.product_main h1::text").get()
    price = response.css("div.product_main p.price_color::text").get()
    rating_classes = response.css("div.product_main p.star-rating::attr(class)").get()
    category = response.css("ul.breadcrumb li:nth-last-child(2) a::text").get()
    availability_text = " ".join(response.css("div.product_main p.availability ::text").getall())
    # The element itself sometimes owns the text, not only its descendants.
    if not availability_text.strip():
        availability_text = " ".join(response.xpath(
            "//div[contains(@class,'product_main')]//p[contains(@class,'availability')]//text()"
        ).getall())
    if not title or not title.strip():
        raise ParseError("Book title is missing")
    if not category or not category.strip():
        raise ParseError("Book category is missing")
    if not rating_classes:
        raise ParseError("Book rating is missing")
    image_relative = response.css("div.item.active img::attr(src)").get()
    image_url = response.urljoin(image_relative) if image_relative else None
    if image_url and urlsplit(image_url).scheme != "https":
        image_url = None
    upc = response.xpath(
        "//table[contains(@class,'table-striped')]//tr[th[normalize-space()='UPC']]/td/text()"
    ).get()
    return {
        "source_url": url,
        "title": " ".join(title.split()),
        "price_pence": parse_price(price),
        "rating": parse_rating(rating_classes.split()),
        "category": " ".join(category.split()),
        "availability": parse_availability(availability_text),
        "image_url": image_url,
        "upc": upc.strip() if upc else None,
    }
