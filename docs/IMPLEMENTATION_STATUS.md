# CrawlInsight — Implementation Status & Handoff

**Version:** Code baseline 1.0 · **Basis:** SRS 2.0 (10-day implementation) · **Date:** 2026-10-21

## Meaning of states

- **Implemented:** Code is written and wired to the intended module/interface.
- **Offline-verified:** Executed automated test in this authoring environment.
- **Live verification pending:** Requires dependency installation, Windows browser and/or real Books to Scrape network calls.
- **Not planned:** SRS marks it outside 10-day scope. **Do not implement without change approval.**

This source is **not** an assertion that every function has passed live integration. It must be tested on the team's machine before acceptance.

## FR checklist

| FR | Module | Implementation | Verification status / next task |
|---|---|---|---|
| FR-01 summary | `src/db.py`, `app.py`, `dashboard.js` | Implemented | SQLite empty-state offline verified; Flask UI runtime pending |
| FR-02 max_pages selection | `dashboard.html`, `app.py` | Implemented | Python strict type checks tested; POST runtime pending |
| FR-03 Start Crawl | `app.py`, `crawler/run_job.py` | Implemented | Subprocess call covered by Flask test but that test not executed here |
| FR-04 poll 2s | `dashboard.js` | Implemented | Manual Chrome test pending |
| FR-05 5 recent jobs | `src/db.py`, `dashboard.js` | Implemented | DB query offline verified; visual check pending |
| FR-06 rating distribution | `src/db.py`, `dashboard.js` | Implemented | SQL counts offline verified; browser chart check pending |
| FR-07 allowlisted HTTPS | `crawler/parser.py`, spider | Implemented | URL helper offline verified; live redirect/robots check pending |
| FR-08 Next pagination | `crawler/spiders/books_spider.py` | Implemented | **Live test max_pages=2 pending** |
| FR-09 detail requests | spider/parser | Implemented | **Live extraction pending** |
| FR-10 HTML parsing/validation | `crawler/parser.py`, `src/db.py` | Implemented | Pure parsing helpers verified; HtmlResponse fixture test skipped until Scrapy installed |
| FR-11 robots and throttling | `crawler/settings.py` | Implemented | Settings offline verified; live run check pending |
| FR-12 HTTP/parse failure | spider callbacks, DB counter | Implemented | Live network failure and unknown HTML need manual verification |
| FR-13 job states | `src/db.py`, `crawler/run_job.py` | Implemented | State transitions tested offline; child process completion pending |
| FR-14 single active job | `src/db.py`, `app.py` | Implemented | SQLite transaction verified; simultaneous HTTP test pending |
| FR-15 UNIQUE/upsert | `schema.sql`, `src/db.py` | Implemented | Offline duplicate test PASS |
| FR-16 counters | `src/db.py` | Implemented | Atomic counters and CHECK invariant tested offline |
| FR-17 JSON errors | `app.py` | Implemented | Flask status-code test requires installed Flask |
| FR-18 pagination | `src/db.py`, `books.js` | Implemented | SQL paging offline verified; manual visual test pending |
| FR-19 title search | `src/db.py`, `books.js` | Implemented | Offline SQL matching test PASS |
| FR-20 price filter | `src/db.py`, `books.js` | Implemented | Decimal validation offline PASS |
| FR-21 card fields/link safety | `books.js`, `books.html` | Implemented | DOM constructed safely; manual browser review pending |

## Current automated result (authoring environment)

- `python -m pytest -q`: **28 passed, 4 skipped** (Flask/Scrapy test modules unavailable due to network/package installation restrictions).
- SQLite schema created and verified via tests; no production dataset was preloaded.
- Cannot claim Scrapy live crawling, Flask end-to-end or Windows setup succeeded **until teammates run them**. Report actual results and attach screenshots under `docs/screenshots/`.

## Important integration checks on team Windows machines

1. Create fresh venv; run `pip install -r requirements.txt`. Check exact installed versions and Python minor version.
2. Run full pytest. All skipped tests that were skipped for missing packages should execute once dependencies are installed.
3. Run `python app.py`. Open DevTools Console/Network; check Dashboard and Explorer desktop/mobile.
4. Start 1-page crawl. Watch subprocess logs `data/logs/crawl-job-N.log` and confirm terminal state.
5. Check item fields / parser selectors against **live** book detail; adjust parser only if actually different, with fixture/test updates.
6. Start 2-page crawl; prove link Next follows correctly and saves book details.
7. Repeat job to confirm `existing_books > 0` and constant `COUNT(books)`.
8. Test source outage/timeout/robots policy without bypassing restrictions; verify previous books survive.
9. Test 409 via concurrent requests; refresh Dashboard while run active; Book Explorer filters and mobile display.
10. Capture real screenshots/logs for report; distinguish successful live verification from locally mocked fixtures.

## Known limitations by design, not blockers

- No process supervisor / auto recovery if OS kills child; manual recovery command exists.
- No accounts/public deployment, no arbitrary URLs, no CSV, no historical price chart.
- Responsive layout aims at usability on 390px but Chrome/Edge testing on actual devices is needed.
- Site may change or become temporarily unavailable; this cannot be solved by adding fake product data.

## Before merging additional work

Use `SRS_CrawlInsight_10Days.md` as source of truth. If adding a feature outside FR-01..21, write a scoped change request and assess effect on 10-day deadline. Formal assignment/schedule will be created **after** code review in the follow-up requested by the project lead.
