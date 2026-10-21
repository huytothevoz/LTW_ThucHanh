"""Safety policy does not require the third-party Scrapy package to import."""
from crawler.settings import SETTINGS


def test_safe_crawler_settings():
    assert SETTINGS["ROBOTSTXT_OBEY"] is True
    assert SETTINGS["CONCURRENT_REQUESTS"] <= 1
    assert SETTINGS["CONCURRENT_REQUESTS_PER_DOMAIN"] <= 1
    assert SETTINGS["DOWNLOAD_DELAY"] >= 1.0
    assert SETTINGS["RETRY_ENABLED"] is True
    assert SETTINGS["RETRY_TIMES"] <= 1
    assert SETTINGS["DOWNLOADER_MIDDLEWARES"]["crawler.middlewares.StrictSourceMiddleware"] == 120
