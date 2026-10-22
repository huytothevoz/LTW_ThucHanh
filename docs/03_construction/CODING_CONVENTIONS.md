# CrawlInsight — Coding & Collaboration Conventions

**Scope:** These are **CrawlInsight-specific** rules. They inherit useful general teamwork practices, but do **not** use the PHP/PSR or MySQL-specific parts of unrelated projects.

## Code rules

1. `PHP`: PHP 8.2+, PSR-12, Laravel conventions, strict input validation, parameterized SQL, and explicit error responses. Keep controllers thin and place domain operations in `app/Services/`.
2. `Python`: PEP 8, `snake_case`, `PascalCase` classes, and type hints where helpful; use it for `crawler/` and crawler-side SQLite persistence only.
3. `JavaScript`: `camelCase` variable/function, `UPPER_SNAKE_CASE` constants. All external text inserted using `textContent`, not untrusted `innerHTML`. Use `defer`; no JS in inline HTML attributes.
4. `Twig`, CSS, and HTML: use the existing Twig renderer, hyphenated classes/IDs, and semantic tags. Keep user-visible text in localization resources.
5. **API/database contract:** all JSON properties and SQL columns remain **`snake_case`** (`max_pages`, `items_saved`, `price_pence`). Do not rename keys without updating API documentation, frontend, and tests.
6. No hard-coded book arrays or counterfeit outputs in production UI. Python test fixtures stay in `tests/fixtures/` only.
7. SQL must be parameterized; all upsert+counter changes are atomic. Never write secrets, tokens or absolute machine-specific paths into source.
8. Error messages to end users are safe and concise; detailed exceptions go to local logs.
9. One source: only `books.toscrape.com` HTTPS; no user-controlled URL; respect robots and delay by default.

## Team review rules

- `main` stays stable; work in `feature/...`, `fix/...`, `docs/...` branches and merge via PR.
- Each PR describes relevant FR IDs and tests, and does not silently change field/endpoint contracts.
- Commit messages example `feat(crawler): follow catalogue pagination`, `fix(api): reject boolean max_pages`, `test(db): cover duplicate upsert`.
- Review `git status`, `git diff`, execute `scripts/run_tests_windows.ps1`, test endpoint changes in UI before merge.
- Never force-push shared main, delete `htdocs`, reset another project's DB or commit `.venv`, `.env` or runtime SQLite files.

## Minimum code review checklist

- [ ] Requirement stated in SRS and not an out-of-scope addition.
- [ ] API JSON, DB schema, item field names unchanged or documented migration approved.
- [ ] Reproducible test(s) provided; production code does not use test fixture.
- [ ] Mobile empty/loading/error states handled, keyboard focus preserved.
- [ ] URL allowlist, SQL binding, response text escaping remain intact.
- [ ] README and status file updated where a behavior has changed.
