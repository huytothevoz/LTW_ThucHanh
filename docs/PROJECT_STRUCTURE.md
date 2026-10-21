# LTW-TH — cấu trúc code V4 (source thực tế)

```text
LTW-TH/
├── START_HERE.bat                       # Setup and run on Windows
├── app.py                               # Flask factory/router, global guards, crawl launch
├── .env.example                         # Optional SMTP, port, secret and local reset configuration
├── README.md                            # Install, features, manual acceptance checklist
├── PROJECT_STRUCTURE.md                 # This map of module ownership
├── requirements.txt                     # Flask, Scrapy, pytest
├── src/
│   ├── db.py                            # Stable facade imported by crawler and older code
│   ├── i18n.py                          # Vietnamese + English server text dictionary
│   ├── database/
│   │   ├── connection.py               # Path outside Apache htdocs, SQLite connection
│   │   ├── migrations.py               # Additive 001..004 migrations, backup on upgrade
│   │   ├── books.py                    # HTML result validation, book/category upserts
│   │   ├── jobs.py                     # Crawl-job status and evidence
│   │   ├── analytics.py                # Global catalogue counters
│   │   └── accounts.py                 # User, password hashes, bookmarks, preferences, saved filters
│   └── web/
│       ├── auth.py                     # Login/register/logout, recovery, profile API
│       ├── security.py                 # Session guard, anti-CSRF utilities
│       ├── workspace.py                # Pages and personal/workspace APIs
│       └── mail.py                     # SMTP sender for password recovery
├── database/
│   ├── schema.sql                      # V4 fresh-install SQL reference
│   ├── migrations/
│   │   ├── 001_core.sql                # Initial crawler data model
│   │   ├── 002_indexes.sql             # Indexes
│   │   ├── 003_views.sql               # Read-only SQL views
│   │   └── 004_identity_and_workspace.sql # Users and personalization
│   ├── tools/                            # CLI tables/rows/describe/check/export and report
│   ├── examples/                         # Synthetic demo SQLite + HTML viewer
│   ├── README.md, DATA_DICTIONARY.md, SQL_RECIPES.md
├── crawler/                             # Scrapy spider, parser, pipeline, policies and runner
├── templates/
│   ├── base.html, _icons.html           # Shared layout and SVG macro
│   ├── index.html                       # Public landing page
│   ├── auth.html                        # Login/register/recovery/reset (same design)
│   ├── dashboard.html                   # /workspace
│   ├── books.html                       # /books, filter/save/detail modals
│   ├── saved.html                       # /saved
│   ├── history.html                     # /history
│   ├── analytics.html                   # /analytics
│   ├── sources.html                     # /sources
│   ├── settings.html                    # /settings
│   ├── help.html                        # /help
│   └── 404.html, 500.html
├── static/
│   ├── css/style.css                    # Existing crawler dashboard/book explorer styles
│   ├── css/platform.css                 # V4 design system, public/auth/workspace, responsive, dark
│   ├── js/common.js                     # Fetch CSRF, navigation, language, theme, helpers
│   ├── js/auth.js                       # Auth forms and password reset
│   ├── js/dashboard.js                  # Live job state and chart from DB (kept/adapted)
│   ├── js/books.js                      # Filters, pagination, bookmarks, details, saved searches
│   ├── js/workspace-pages.js            # Saved, history, analytics, settings controllers
│   └── img/favicon.svg
├── scripts/                             # PowerShell install/start/test, XAMPP-safe
├── tests/                               # DB, identity, upgrade, parser, API, template tests
├── docs/
│   ├── API.md                           # Older SRS 2.0 API contract (archived)
│   ├── API_V4.md                        # Current API contract
│   ├── IMPLEMENTATION_STATUS_V4.md      # Tested, conditional, outstanding
│   └── ...
└── data/                                # Runtime DB on non-XAMPP install (gitignored)
```

## Database isolation and responsibility

- **Shared real source data**: `books`, `categories`, `sources`, price history, crawl evidence. Avoid one copy of each book per account.
- **User-scoped data**: `users`, `user_preferences`, `bookmarks`, `saved_searches`, and `crawl_jobs.user_id` for jobs created after V4.
- **Sensitive tokens**: hashed `password_reset_tokens`, hashed subject of `auth_attempts`; do not export publicly.
- **Legacy jobs**: V3 jobs migrate with `user_id IS NULL`; historical rows stay intact without accidentally attaching them to a new user.

## Ownership and conflict prevention

1. Identity/login/password recovery: `src/web/auth.py` + `src/database/accounts.py` + `templates/auth.html`.
2. Existing crawler: `crawler/*`, `src/database/books.py`, `src/database/jobs.py` — do not rewrite without tests.
3. Frontend platform: `templates/*`, `static/css/platform.css`, `static/js/*` (split controllers by page).
4. API integration: `src/web/workspace.py` and `app.py` route registration; preserve `/api/books`, `/api/jobs`, `/api/summary` contracts.
5. Schema: add new `005_*.sql` migrations rather than editing `004_*.sql` after release. Record every new DB table in DATA_DICTIONARY and write upgrade tests.

Do not modify XAMPP installation or delete `htdocs`. Do not commit `.env`, live DB, session secret or user-generated reports.
