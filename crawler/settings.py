"""Scrapy configuration; protect the educational sandbox from aggressive requests."""
SETTINGS = {
    "BOT_NAME": "crawlinsight",
    "ROBOTSTXT_OBEY": True,
    "CONCURRENT_REQUESTS": 1,
    "CONCURRENT_REQUESTS_PER_DOMAIN": 1,
    "DOWNLOAD_DELAY": 1.0,
    "DOWNLOAD_TIMEOUT": 12,
    "RETRY_ENABLED": True,
    "RETRY_TIMES": 1,
    "USER_AGENT": "CrawlInsight-StudentDemo/1.0 (educational crawl)",
    "LOG_LEVEL": "INFO",
    "COOKIES_ENABLED": False,
    "TELNETCONSOLE_ENABLED": False,
    "DOWNLOADER_MIDDLEWARES": {"crawler.middlewares.StrictSourceMiddleware": 120},
    "ITEM_PIPELINES": {"crawler.pipelines.SQLiteBookPipeline": 300},
}
