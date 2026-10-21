"""Public API summary queries; projections keep existing frontend contract."""
from .connection import connect,row_dict


def summary()->dict:
    with connect() as con:
        total=con.execute('SELECT COUNT(*) FROM books').fetchone()[0]
        completed=con.execute("SELECT COUNT(*) FROM crawl_jobs WHERE status='COMPLETED'").fetchone()[0]
        recent=[dict(row) for row in con.execute('SELECT id,status,max_pages,items_saved,created_at FROM crawl_jobs ORDER BY id DESC LIMIT 5')]
        last=con.execute('SELECT id,status,created_at FROM crawl_jobs ORDER BY id DESC LIMIT 1').fetchone()
        ratings={r['rating']:r['count'] for r in con.execute('SELECT rating,COUNT(*) count FROM books GROUP BY rating')}
    return {'total_books':total,'completed_jobs':completed,'last_job':row_dict(last),'recent_jobs':recent,'rating_distribution':[{'rating':i,'count':ratings.get(i,0)} for i in range(1,6)]}
