"""Job lifecycle, page evidence and sanitized crawler event logging."""
from __future__ import annotations
from .connection import connect, now_utc, row_dict

ACTIVE_STATUSES = {'PENDING','RUNNING'}
TERMINAL_STATUSES = {'COMPLETED','FAILED'}


class ActiveJobError(Exception):
    """Only one running or pending crawl is permitted."""


def sanitize_error(message: str | None) -> str | None:
    if not message:
        return None
    return ' '.join(str(message).split())[:220]


def create_job(max_pages: int, source_id: int = 1, user_id: int | None = None) -> dict:
    if type(max_pages) is not int or max_pages not in (1, 2, 3, 4, 5):
        raise ValueError('max_pages must be an integer from 1 to 5')
    if type(source_id) is not int or source_id not in (1, 2, 3):
        raise ValueError('source_id must be 1, 2, or 3')
    with connect() as con:
        con.execute('BEGIN IMMEDIATE')
        active = con.execute(
            "SELECT id FROM crawl_jobs WHERE COALESCE(user_id,0)=COALESCE(?,0) "
            "AND status IN ('PENDING','RUNNING') LIMIT 1",
            (user_id,),
        ).fetchone()
        if active:
            raise ActiveJobError(f"Crawl #{active['id']} is still active")
        cur = con.execute(
            "INSERT INTO crawl_jobs(source_id,max_pages,status,created_at,user_id) VALUES(?,?,'PENDING',?,?)",
            (source_id,max_pages,now_utc(),user_id),
        )
        con.execute("INSERT INTO crawl_events(job_id,level,event_type,message,created_at) VALUES(?,'INFO','CREATED','Crawl job created',?)", (cur.lastrowid,now_utc()))
        return dict(con.execute('SELECT * FROM crawl_jobs WHERE id=?',(cur.lastrowid,)).fetchone())


def get_job(job_id: int) -> dict | None:
    with connect() as con:
        return row_dict(con.execute('SELECT * FROM crawl_jobs WHERE id=?',(job_id,)).fetchone())


def mark_job_running(job_id: int) -> bool:
    with connect() as con:
        result = con.execute("UPDATE crawl_jobs SET status='RUNNING',started_at=? WHERE id=? AND status='PENDING'", (now_utc(),job_id))
        if result.rowcount:
            con.execute("INSERT INTO crawl_events(job_id,level,event_type,message,created_at) VALUES(?,'INFO','STARTED','Crawler process started',?)",(job_id,now_utc()))
        return result.rowcount == 1


def finish_job(job_id: int, status: str, reason: str | None = None) -> None:
    if status not in TERMINAL_STATUSES:
        raise ValueError('Invalid terminal status')
    clean = sanitize_error(reason)
    with connect() as con:
        updated = con.execute("UPDATE crawl_jobs SET status=?,finished_at=?,last_error=COALESCE(?,last_error),error_count=error_count+? WHERE id=? AND status IN ('PENDING','RUNNING')",(status,now_utc(),clean,int(bool(clean)),job_id))
        if updated.rowcount:
            con.execute("INSERT INTO crawl_events(job_id,level,event_type,message,created_at) VALUES(?,?,?,?,?)",(job_id,'ERROR' if status=='FAILED' else 'INFO',status,clean or f'Job {status.lower()}',now_utc()))


def record_error(job_id: int, message: str) -> None:
    clean = sanitize_error(message) or 'Unknown crawl error'
    with connect() as con:
        updated = con.execute("UPDATE crawl_jobs SET error_count=error_count+1,last_error=? WHERE id=? AND status='RUNNING'",(clean,job_id))
        if updated.rowcount:
            con.execute("INSERT INTO crawl_events(job_id,level,event_type,message,created_at) VALUES(?,'ERROR','CRAWLER_ERROR',?,?)",(job_id,clean,now_utc()))


def increment_catalogue(job_id: int, discovered: int) -> None:
    """Compatibility helper for SRS 2 tests. Prefer record_catalogue_page in spider."""
    if type(discovered) is not int or discovered < 0:
        raise ValueError('discovered cannot be negative')
    with connect() as con:
        con.execute("UPDATE crawl_jobs SET catalogue_pages_done=catalogue_pages_done+1,books_found=books_found+? WHERE id=? AND status='RUNNING'",(discovered,job_id))


def record_catalogue_page(job_id: int, page_url: str, page_number: int, discovered: int) -> None:
    """Page evidence and counters committed together. Repeated page is idempotent."""
    if type(discovered) is not int or discovered < 0 or type(page_number) is not int or page_number < 1:
        raise ValueError('Invalid page evidence')
    if not (page_url.startswith('https://books.toscrape.com/') and len(page_url) <= 2000):
        raise ValueError('Unapproved catalogue page URL')
    with connect() as con:
        con.execute('BEGIN IMMEDIATE')
        job=con.execute('SELECT max_pages,status FROM crawl_jobs WHERE id=?',(job_id,)).fetchone()
        if not job or job['status']!='RUNNING' or page_number>job['max_pages']:
            raise RuntimeError('Invalid page/job state')
        inserted=con.execute('INSERT OR IGNORE INTO crawl_pages(job_id,page_number,page_url,books_discovered,visited_at) VALUES(?,?,?,?,?)', (job_id,page_number,page_url,discovered,now_utc()))
        if inserted.rowcount:
            con.execute('UPDATE crawl_jobs SET catalogue_pages_done=catalogue_pages_done+1,books_found=books_found+? WHERE id=?',(discovered,job_id))
        else:
            prior=con.execute('SELECT page_url FROM crawl_pages WHERE job_id=? AND page_number=?',(job_id,page_number)).fetchone()
            if prior is None or prior['page_url'] != page_url:
                raise RuntimeError('Conflicting page_number evidence')


def list_job_events(job_id: int, limit: int=100) -> list[dict]:
    if not 1 <= limit <= 500:
        raise ValueError('limit must be 1–500')
    with connect() as con:
        return [dict(r) for r in con.execute('SELECT id,job_id,level,event_type,message,created_at FROM crawl_events WHERE job_id=? ORDER BY id DESC LIMIT ?', (job_id,limit))]
