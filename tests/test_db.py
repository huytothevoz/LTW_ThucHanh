"""Database contract, transaction invariants, duplicate detection and search."""
import sqlite3

import pytest

from src import db


def test_fresh_database_is_empty(isolated_db):
    result = db.summary()
    assert result["total_books"] == 0
    assert result["completed_jobs"] == 0
    assert result["last_job"] is None
    assert len(result["rating_distribution"]) == 5
    assert all(bucket["count"] == 0 for bucket in result["rating_distribution"])
    assert db.search_books()["total_pages"] == 0


@pytest.mark.parametrize("invalid", [0, 4, "2", 2.0, True, None])
def test_max_pages_strict_types(isolated_db, invalid):
    with pytest.raises(ValueError):
        db.create_job(invalid)


def test_one_active_job_only(isolated_db):
    job = db.create_job(1)
    with pytest.raises(db.ActiveJobError):
        db.create_job(2)
    assert db.mark_job_running(job["id"])
    assert not db.mark_job_running(job["id"])
    with pytest.raises(db.ActiveJobError):
        db.create_job(3)
    db.finish_job(job["id"], "FAILED", "Test failure")
    assert db.create_job(2)["status"] == "PENDING"


def test_books_upsert_and_counter_atomicity(isolated_db, example_book):
    job = db.create_job(1)
    assert db.mark_job_running(job["id"])
    db.increment_catalogue(job["id"], 1)
    assert db.save_book_for_job(job["id"], example_book) == "new"
    book_before = db.search_books()["items"][0]
    with db.connect() as con:
        first_seen = con.execute("SELECT first_seen_at FROM books").fetchone()[0]
    db.finish_job(job["id"], "COMPLETED")
    assert db.summary()["total_books"] == 1
    assert db.get_job(job["id"])["items_saved"] == 1
    assert db.get_job(job["id"])["new_books"] == 1

    next_job = db.create_job(2)
    assert db.mark_job_running(next_job["id"])
    db.increment_catalogue(next_job["id"], 1)
    newer_book = {**example_book, "price_pence": 2099, "title": "Updated book"}
    assert db.save_book_for_job(next_job["id"], newer_book) == "existing"
    after = db.search_books()
    assert after["total"] == 1
    assert after["items"][0]["id"] == book_before["id"]
    assert after["items"][0]["price_pence"] == 2099
    with db.connect() as con:
        assert con.execute("SELECT first_seen_at FROM books").fetchone()[0] == first_seen
    assert db.get_job(next_job["id"])["items_saved"] == 1
    assert db.get_job(next_job["id"])["new_books"] == 0
    assert db.get_job(next_job["id"])["existing_books"] == 1


def test_bad_book_does_not_increase_count(isolated_db, example_book):
    job = db.create_job(1)
    db.mark_job_running(job["id"])
    with pytest.raises(db.InvalidBookError):
        db.save_book_for_job(job["id"], {**example_book, "rating": 8})
    with pytest.raises(db.InvalidBookError):
        db.save_book_for_job(job["id"], {**example_book, "source_url": "https://evil.example/book"})
    assert db.get_job(job["id"])["items_saved"] == 0
    assert db.summary()["total_books"] == 0


def test_filtering_price_and_title(isolated_db, example_book):
    job = db.create_job(1)
    db.mark_job_running(job["id"])
    db.save_book_for_job(job["id"], example_book)
    db.save_book_for_job(job["id"], {
        **example_book, "source_url": "https://books.toscrape.com/catalogue/another_777/index.html",
        "title": "Another title", "price_pence": 4599, "rating": 5,
    })
    assert db.search_books(q="TESTING", min_price="10", max_price="20")["total"] == 1
    assert db.search_books(q="script'")["total"] == 0
    assert db.search_books(min_price="50")["total"] == 0
    assert db.search_books(page=2)["items"] == []
    assert db.summary()["rating_distribution"][3]["count"] == 1
    assert db.summary()["rating_distribution"][4]["count"] == 1


@pytest.mark.parametrize("invalid", ["-1", "10000", "NaN", "1.234", "2e2", "inf", "--", "1,2"])
def test_invalid_price_filters(isolated_db, invalid):
    with pytest.raises(ValueError):
        db.search_books(min_price=invalid)


def test_invalid_price_range(isolated_db):
    with pytest.raises(ValueError):
        db.search_books(min_price="19.99", max_price="19.98")


def test_job_counter_check_constraint(isolated_db):
    job = db.create_job(1)
    with pytest.raises(sqlite3.IntegrityError):
        with db.connect() as connection:
            connection.execute(
                "UPDATE crawl_jobs SET items_saved=5,new_books=2,existing_books=2 WHERE id=?",
                (job["id"],),
            )


def test_create_job_supports_sources(isolated_db):
    with db.connect() as con:
        con.execute("INSERT OR IGNORE INTO sources(id,name,base_url,allowed_host,is_enabled,created_at) VALUES(2,'Open Library','https://openlibrary.org/','openlibrary.org',1,'2026-04-01T00:00:00Z')")
        con.execute("INSERT OR IGNORE INTO sources(id,name,base_url,allowed_host,is_enabled,created_at) VALUES(3,'Project Gutenberg','https://www.gutenberg.org/','www.gutenberg.org',1,'2026-04-01T00:00:00Z')")

    j1 = db.create_job(1, source_id=1)
    assert j1["source_id"] == 1
    db.finish_job(j1["id"], "COMPLETED")

    j2 = db.create_job(2, source_id=2)
    assert j2["source_id"] == 2
    db.finish_job(j2["id"], "COMPLETED")

    j3 = db.create_job(3, source_id=3)
    assert j3["source_id"] == 3
    db.finish_job(j3["id"], "COMPLETED")

    with pytest.raises(ValueError):
        db.create_job(1, source_id=99)


def test_run_job_external_sources(isolated_db):
    from crawler import run_job

    with db.connect() as con:
        con.execute("INSERT OR IGNORE INTO sources(id,name,base_url,allowed_host,is_enabled,created_at) VALUES(2,'Open Library','https://openlibrary.org/','openlibrary.org',1,'2026-04-01T00:00:00Z')")

    j = db.create_job(1, source_id=2)
    exit_code = run_job.run(j["id"])
    assert exit_code == 0
    updated = db.get_job(j["id"])
    assert updated["status"] == "COMPLETED"

    events = db.list_job_events(j["id"])
    event_messages = [e["message"] for e in events]
    assert any("Open Library" in m for m in event_messages)

