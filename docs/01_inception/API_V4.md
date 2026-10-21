# CrawlInsight V4 API contract

All endpoints return JSON (except the CSV export). Same-origin cookies are used for sessions; mutations require `X-CSRF-Token` from the `<meta name="csrf-token">` in the HTML. Anonymous callers get `401 AUTH_REQUIRED` for workspace endpoints. JSON errors have the shape `{ "error": { "code": "...", "message": "..." } }`.

| Method | Endpoint | Login? | Function |
|---|---|---|---|
| GET | `/api/health` | No | Local app health |
| GET | `/api/auth/me` | No | Current user or null and preferences |
| POST | `/api/auth/register` | No | `full_name`, `email`, `password` |
| POST | `/api/auth/login` | No | `email`, `password` |
| POST | `/api/auth/logout` | Yes | Invalidate browser session |
| POST | `/api/auth/request-reset` | No | `email`; generic response, SMTP or local opt-in |
| POST | `/api/auth/reset-password` | No | One-use `token`, `password` |
| PATCH | `/api/me/profile` | Yes | Update `full_name` |
| PATCH | `/api/me/preferences` | Yes | Partial `locale=vi/en`, `theme=light/dark/system`, `book_layout=grid/list` |
| POST | `/api/me/password` | Yes | `current_password`, `new_password`; forces re-login |
| GET | `/api/summary` | Yes | Global books/ratings + this user's latest jobs/bookmarks |
| POST | `/api/jobs` | Yes | `{ "max_pages": 1|2|3 }`, 202 queued or 409 active |
| GET | `/api/jobs/{id}` | Owner | One crawl job and its events |
| GET | `/api/history` | Yes | Own latest 100 crawl sessions |
| GET | `/api/books` | Yes | `q`, `min_price`, `max_price`, `page`, plus `bookmarked_ids` |
| GET | `/api/books/{id}` | Yes | One original book plus price history |
| GET | `/api/bookmarks` | Yes | Own saved books (`page`) |
| POST / DELETE | `/api/bookmarks/{id}` | Yes | Add/remove one book in own saved list |
| GET / POST | `/api/saved-searches` | Yes | List/save personal filters (`name`, `q`, `min_price`, `max_price`) |
| DELETE | `/api/saved-searches/{id}` | Owner | Delete personal saved filter |
| GET | `/api/analytics` | Yes | Global source-category/rating/GBP price stats |
| GET | `/api/sources` | Yes | Approved source records |
| GET | `/api/exports/books.csv` | Yes | UTF-8 BOM CSV of the shared catalogue |

**Scope choice:** book entries are global public-domain test-source observations and **not** duplicated per account. Each authenticated account gets its own bookmarks, saved searches, preferences and newly created crawl jobs. Only one globally active crawler job is permitted, for source-rate safety. The current crawler accepts only Books to Scrape and max 3 catalogue pages.

**Security:** no password hashes or reset tokens appear in API responses; email reset links are shown only with `TESTING` or explicit `ALLOW_LOCAL_RESET_LINKS=1` on localhost. The `CSRF` meta value changes on login/logout. Test the API using the browser or a client that preserves the same cookie jar and sends the CSRF header.
