# CrawlInsight API Contract — v2

Base URL: `http://127.0.0.1:5000`. All JSON APIs begin with `/api`. Field names are `snake_case` exactly as in SRS §8. JSON examples below are **contract illustrations**, never production fixture data.

## 1. GET `/api/summary`

HTTP 200:

```json
{
  "total_books": 0,
  "completed_jobs": 0,
  "last_job": null,
  "rating_distribution": [
    {"rating": 1, "count": 0},
    {"rating": 2, "count": 0},
    {"rating": 3, "count": 0},
    {"rating": 4, "count": 0},
    {"rating": 5, "count": 0}
  ],
  "recent_jobs": []
}
```

`recent_jobs` max 5 records, newest first (`id DESC`). Each record: `id`, `status`, `max_pages`, `items_saved`, `created_at`. `last_job` contains `id`, `status`, `created_at` or null.

## 2. POST `/api/jobs`

Request `Content-Type: application/json`:

```json
{"max_pages": 1}
```

Body must be **exactly** this one key, integer 1/2/3. Reject booleans, floats, strings, extra fields, missing value. Success HTTP **202**:

```json
{"job":{"id":1,"status":"PENDING","max_pages":1,"created_at":"2026-10-21T10:05:00Z"}}
```

- 400 `INVALID_MAX_PAGES`: malformed request
- 409 `JOB_ALREADY_ACTIVE`: existing PENDING/RUNNING
- 503 `CRAWLER_LAUNCH_FAILED`: process could not start, job marked FAILED

All errors use `{"error":{"code":"...","message":"..."}}`.

## 3. GET `/api/jobs/<id>`

HTTP 200: `{"job":{...}}` includes fields defined by `database/schema.sql`: `id`, `max_pages`, `status`, `catalogue_pages_done`, `books_found`, `items_saved`, `new_books`, `existing_books`, `error_count`, `last_error`, `created_at`, `started_at`, `finished_at`. Status is only `PENDING`, `RUNNING`, `COMPLETED`, `FAILED`.

HTTP 404 `JOB_NOT_FOUND` for unknown id.

## 4. GET `/api/books`

Query params:

| Param | Type | Validation |
|---|---|---|
| `q` | string | <=100 chars, case-insensitive title substring; %/_ escaped |
| `min_price` | decimal string GBP | optional, 0..9999.99, <=2 fractional digits |
| `max_price` | decimal string GBP | optional, min<=max |
| `page` | positive integer | 1..100000; default 1 |

HTTP 200:

```json
{
  "items": [
    {"id":1,"title":"Example (schema only)","price_pence":1299,"rating":4,
     "category":"Travel","availability":"In stock","image_url":null,
     "source_url":"https://books.toscrape.com/catalogue/example_999/index.html"}
  ],
  "page":1,"page_size":12,"total":1,"total_pages":1
}
```

Books are ordered by `books.id DESC`, 12 per page. Out-of-bounds page returns 200 with empty items and correct `total/total_pages`. HTTP 400 `INVALID_FILTER` for invalid data. All SQL parameters use bound placeholders; never place raw query params in SQL text.

## 5. HTML routes

- `/` Dashboard + Crawl form + job monitor + rating chart + last 5 jobs.
- `/books` searchable/filtered book catalogue.
- No additional endpoints or arbitrary-source crawling without approved SRS change.

## 6. Manual testing (PowerShell)

```powershell
Invoke-RestMethod http://127.0.0.1:5000/api/summary
Invoke-RestMethod http://127.0.0.1:5000/api/books
Invoke-RestMethod http://127.0.0.1:5000/api/jobs -Method Post -ContentType 'application/json' -Body '{"max_pages":1}'
Invoke-RestMethod http://127.0.0.1:5000/api/books?q=Testing`&min_price=10`&max_price=40
```

Last example may need URL quoted with backticks escaped correctly in the shell; simpler in browser: `/api/books?q=Testing&min_price=10&max_price=40`.
