"""Test database is always isolated; tests never touch real CrawlInsight data."""
import pytest
from src import db


@pytest.fixture
def isolated_db(tmp_path, monkeypatch):
    db_file = tmp_path / "test_crawlinsight.db"
    monkeypatch.setenv("CRAWLINSIGHT_DB_PATH", str(db_file))
    db.init_db()
    yield db_file


@pytest.fixture
def example_book():
    return {
        "source_url": "https://books.toscrape.com/catalogue/testing_777/index.html",
        "title": "Testing with Real Database Logic",
        "price_pence": 1234,
        "rating": 4,
        "category": "Science",
        "availability": "In stock",
        "image_url": None,
        "upc": "TEST-777",
    }
