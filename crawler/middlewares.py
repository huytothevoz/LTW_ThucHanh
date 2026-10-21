"""Final network guard: block off-source or insecure requests, even after redirects.

Scrapy's allowed_domains protects normal link following. This downloader
middleware additionally rejects HTTP or off-host redirect destinations.
"""
from urllib.parse import urlsplit

from scrapy.exceptions import IgnoreRequest


def is_approved_request_url(url: str) -> bool:
    try:
        parts = urlsplit(url)
        return (parts.scheme == "https" and parts.hostname == "books.toscrape.com"
                and parts.username is None and parts.password is None
                and parts.port is None)
    except ValueError:
        return False


class StrictSourceMiddleware:
    def process_request(self, request, spider):
        if not is_approved_request_url(request.url):
            spider.logger.warning("Blocked off-source or insecure request")
            raise IgnoreRequest("Request rejected by CrawlInsight source allowlist")
        return None
