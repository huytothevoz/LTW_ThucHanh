"""Offline listing follow-links test; requires Scrapy package installed."""
from pathlib import Path

import pytest

scrapy = pytest.importorskip('scrapy')
from scrapy.http import HtmlResponse, Request

from crawler.spiders.books_spider import BooksSpider


def test_catalogue_schedules_unique_details_and_real_next(monkeypatch):
    records = []
    monkeypatch.setattr('crawler.spiders.books_spider.db.increment_catalogue',
                        lambda job_id, discovered: records.append((job_id, discovered)))
    spider = BooksSpider(job_id=12, max_pages=2)
    url = 'https://books.toscrape.com/'
    html = (Path(__file__).parent / 'fixtures' / 'catalogue.html').read_bytes()
    response = HtmlResponse(url=url, body=html, encoding='utf-8', request=Request(url))
    emitted = list(spider.parse(response))
    detail = [request for request in emitted if request.meta.get('kind') == 'detail']
    next_pages = [request for request in emitted if request.meta.get('kind') == 'catalogue']
    assert records == [(12, 2)]
    assert len(detail) == 2
    assert len(next_pages) == 1
    assert next_pages[0].url == 'https://books.toscrape.com/catalogue/page-2.html'
    assert next_pages[0].cb_kwargs['page_number'] == 2


def test_one_page_does_not_follow_next(monkeypatch):
    monkeypatch.setattr('crawler.spiders.books_spider.db.increment_catalogue',
                        lambda job_id, discovered: None)
    spider = BooksSpider(job_id=13, max_pages=1)
    url = 'https://books.toscrape.com/'
    html = (Path(__file__).parent / 'fixtures' / 'catalogue.html').read_bytes()
    response = HtmlResponse(url=url, body=html, encoding='utf-8', request=Request(url))
    assert len(list(spider.parse(response))) == 2
