# CrawlInsight — Coding & Collaboration Conventions

**Scope:** These are **CrawlInsight-specific** rules. They inherit useful general teamwork practices, but do **not** use the PHP/PSR or MySQL-specific parts of unrelated projects.

## Code rules

1. `Python`: PEP 8, function/variable/module names `snake_case`; class names `PascalCase`; constants `UPPER_SNAKE_CASE`; type hints where helpful; pure parsing functions in `crawler/parser.py`.
2. `JavaScript`: `camelCase` variable/function, `UPPER_SNAKE_CASE` constants. All external text inserted using `textContent`, not untrusted `innerHTML`. `defer` scripts; no JS in inline HTML attributes.
3. `CSS/HTML`: hyphenated classes/IDs and meaningful semantic tags. UX text in **English** for midterm demo; code comments/team notes may use Vietnamese with correct UTF-8 diacritics.
4. **Exception for API/database:** all JSON properties and SQL columns remain **`snake_case` from SRS 2.0** (`max_pages`, `items_saved`, `price_pence`). Never rename to camelCase just to follow a general rule, as it would break contract.
5. No hard-coded book arrays or counterfeit outputs in production UI. Unit test HTML fixtures stay in `tests/fixtures/` only.
6. SQL must be parameterized; all upsert+counter changes are atomic. Never write secrets, tokens or absolute machine-specific `C:\...` paths into source.
7. Error messages to end users are safe and concise; detailed tracebacks go to local logs.
8. One source: only `books.toscrape.com` HTTPS; no user-controlled URL; respect robots and delay by default.

## Team review rules

- `main` stays stable; work in `feature/...`, `fix/...`, `docs/...` branches and merge via PR.
- Each PR describes relevant FR IDs and tests, and does not silently change field/endpoint contracts.
- Commit messages example `feat(crawler): follow catalogue pagination`, `fix(api): reject boolean max_pages`, `test(db): cover duplicate upsert`.
- Review `git status`, `git diff`, execute `python -m pytest -q`, test endpoint changes in UI before merge.
- Never force-push shared main, delete `htdocs`, reset another project's DB or commit `.venv`, `.env` or runtime SQLite files.

## Minimum code review checklist

- [ ] Requirement stated in SRS and not an out-of-scope addition.
- [ ] API JSON, DB schema, item field names unchanged or documented migration approved.
- [ ] Reproducible test(s) provided; production code does not use test fixture.
- [ ] Mobile empty/loading/error states handled, keyboard focus preserved.
- [ ] URL allowlist, SQL binding, response text escaping remain intact.
- [ ] README and status file updated where a behavior has changed.
