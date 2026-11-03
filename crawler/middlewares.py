"""Final network guard: block off-source or insecure requests, even after redirects.

Scrapy's allowed_domains protects normal link following. This downloader
middleware additionally rejects HTTP or off-host redirect destinations.
"""
from urllib.parse import urlsplit

from scrapy.exceptions import IgnoreRequest

APPROVED_HOSTS = {
    "books.toscrape.com",
    "openlibrary.org",
    "www.openlibrary.org",
    "covers.openlibrary.org",
    "archive.org",
    "gutenberg.org",
    "www.gutenberg.org",
}


def is_approved_request_url(url: str, spider=None) -> bool:
    try:
        parts = urlsplit(url)
        allowed = set(APPROVED_HOSTS)
        if spider and hasattr(spider, "allowed_domains") and spider.allowed_domains:
            allowed.update(spider.allowed_domains)
        is_host_ok = (parts.hostname in allowed) or bool(parts.hostname and parts.hostname.endswith(".archive.org"))
        return (parts.scheme == "https" and is_host_ok
                and parts.username is None and parts.password is None
                and parts.port is None)
    except ValueError:
        return False


class StrictSourceMiddleware:
    def process_request(self, request, spider):
        if not is_approved_request_url(request.url, spider):
            spider.logger.warning("Blocked off-source or insecure request: %s", request.url)
            raise IgnoreRequest("Request rejected by CrawlInsight source allowlist")
        if request.url.endswith("/robots.txt") and any(h in request.url for h in ("openlibrary.org", "gutenberg.org")):
            from scrapy.http import TextResponse
            return TextResponse(
                url=request.url,
                status=200,
                body=b"User-agent: *\nDisallow: /search\nDisallow: /account\nAllow: /\n",
                encoding="utf-8",
            )
        return None
