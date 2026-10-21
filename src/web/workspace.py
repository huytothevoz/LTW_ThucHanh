"""Authenticated read APIs, personal saved objects, and page routes."""
from __future__ import annotations
from flask import Blueprint,g,jsonify,render_template,request,Response
from src import db
from src.database import accounts as a
from src.web.security import api_error,require_login

workspace=Blueprint('workspace',__name__)

PAGES = {
 '/workspace':('dashboard.html','overview'),
 '/books':('books.html','catalog'),
 '/saved':('saved.html','bookmarks'),
 '/history':('history.html','history'),
 '/analytics':('analytics.html','analytics'),
 '/sources':('sources.html','sources'),
 '/settings':('settings.html','settings'),
 '/help':('help.html','guide'),
}
for path, (template, active) in PAGES.items():
    def page(template=template,active=active):
        return render_template(template,active_page=active)
    workspace.add_url_rule(path, endpoint='page_'+active,view_func=require_login(page))


def user_summary(user_id):
    result=db.summary()
    with db.connect() as con:
        result['completed_jobs']=con.execute("SELECT COUNT(*) FROM crawl_jobs WHERE user_id=? AND status='COMPLETED'",(user_id,)).fetchone()[0]
        result['recent_jobs']=[dict(row) for row in con.execute('SELECT id,status,max_pages,items_saved,created_at FROM crawl_jobs WHERE user_id=? ORDER BY id DESC LIMIT 5',(user_id,))]
        last=con.execute('SELECT id,status,created_at FROM crawl_jobs WHERE user_id=? ORDER BY id DESC LIMIT 1',(user_id,)).fetchone()
        result['last_job']=dict(last) if last else None
        result['saved_books']=con.execute('SELECT COUNT(*) FROM bookmarks WHERE user_id=?',(user_id,)).fetchone()[0]
    return result


@workspace.get('/api/summary')
@require_login
def summary_api():return jsonify(user_summary(g.user['id']))


@workspace.get('/api/books')
@require_login
def books_api():
    try:
        page=int(request.args.get('page','1')) if request.args.get('page','1').isascii() and request.args.get('page','1').isdecimal() else 0
        result=db.search_books(q=request.args.get('q',''),min_price=request.args.get('min_price'),max_price=request.args.get('max_price'),page=page)
    except ValueError as e:return api_error('INVALID_FILTER',str(e),400)
    result['bookmarked_ids']=a.bookmark_ids(g.user['id'],[item['id'] for item in result['items']])
    return jsonify(result)


@workspace.get('/api/books/<int:book_id>')
@require_login
def book_detail_api(book_id):
    with db.connect() as con:
        row=con.execute('SELECT * FROM v_books_detail WHERE id=?',(book_id,)).fetchone()
        if not row:return api_error('BOOK_NOT_FOUND','Không tìm thấy sách.',404)
        book=dict(row)
        price_history=[dict(r) for r in con.execute('SELECT old_price_pence,new_price_pence,changed_at FROM book_price_history WHERE book_id=? ORDER BY id DESC LIMIT 30',(book_id,))]
    return jsonify({'book':book,'is_bookmarked':book_id in a.bookmark_ids(g.user['id'],[book_id]),'price_history':price_history})


@workspace.route('/api/bookmarks/<int:book_id>',methods=['POST','DELETE'])
@require_login
def bookmark_api(book_id):
    if request.method=='DELETE':return jsonify(a.remove_bookmark(g.user['id'],book_id))
    result=a.add_bookmark(g.user['id'],book_id)
    return jsonify(result) if result else api_error('BOOK_NOT_FOUND','Không tìm thấy sách.',404)


@workspace.get('/api/bookmarks')
@require_login
def bookmarks_api():
    try:page=int(request.args.get('page','1'))
    except ValueError: return api_error('INVALID_PAGE','Trang không hợp lệ.',400)
    try:result=a.list_bookmarks(g.user['id'],page)
    except a.AccountError as e:return api_error('INVALID_PAGE',str(e),400)
    return jsonify(result)


@workspace.route('/api/saved-searches', methods=['GET','POST'])
@require_login
def saved_search_api():
    if request.method=='GET': return jsonify({'items':a.list_searches(g.user['id'])})
    data=request.get_json(silent=True) or {}
    try:
        item=a.save_search(g.user['id'],data.get('name',''),str(data.get('q','')),str(data.get('min_price','')),str(data.get('max_price','')))
    except (a.AccountError,ValueError) as e:return api_error('VALIDATION_ERROR',str(e),400)
    return jsonify({'item':item}),201


@workspace.delete('/api/saved-searches/<int:search_id>')
@require_login
def delete_saved_search(search_id):
    if not a.delete_search(g.user['id'],search_id):return api_error('NOT_FOUND','Không tìm thấy bộ lọc.',404)
    return jsonify({'ok':True})


@workspace.get('/api/history')
@require_login
def history_api():
    with db.connect() as con:
        jobs=[dict(r) for r in con.execute('SELECT id,status,max_pages,catalogue_pages_done,books_found,items_saved,new_books,existing_books,error_count,created_at,started_at,finished_at FROM crawl_jobs WHERE user_id=? ORDER BY id DESC LIMIT 100',(g.user['id'],))]
    return jsonify({'items':jobs})


@workspace.get('/api/analytics')
@require_login
def analytics_api():
    with db.connect() as con:
        by_category=[dict(r) for r in con.execute('SELECT category,total_books,average_price_gbp FROM v_category_summary ORDER BY total_books DESC,category LIMIT 12')]
        stat=con.execute('SELECT MIN(price_pence) minimum,MAX(price_pence) maximum,ROUND(AVG(price_pence)) average,COUNT(*) total FROM books').fetchone()
        stats=dict(stat)
    return jsonify({'categories':by_category,'prices':stats,'rating_distribution':db.summary()['rating_distribution']})


@workspace.get('/api/sources')
@require_login
def sources_api():
    with db.connect() as con:
        sources=[dict(r) for r in con.execute('SELECT id,name,base_url,allowed_host,is_enabled,created_at FROM sources ORDER BY id')]
    return jsonify({'items':sources})


@workspace.get('/api/exports/books.csv')
@require_login
def export_books():
    import csv,io
    from flask import stream_with_context
    def generate():
        yield '\ufeff' # Excel UTF-8 BOM
        output=io.StringIO()
        writer=csv.writer(output)
        writer.writerow(['id','title','price_gbp','rating','category','availability','source_url'])
        yield output.getvalue();output.seek(0);output.truncate(0)
        # Bounded batches; no user-supplied SQL fragment or filename.
        with db.connect() as con:
            cur=con.execute('SELECT b.id,b.title,b.price_pence,b.rating,c.name,b.availability,b.source_url FROM books b JOIN categories c ON c.id=b.category_id ORDER BY b.id')
            for row in cur:
                writer.writerow([row[0],row[1],f'{row[2]/100:.2f}',row[3],row[4],row[5],row[6]])
                yield output.getvalue();output.seek(0);output.truncate(0)
    return Response(stream_with_context(generate()),mimetype='text/csv; charset=utf-8',headers={'Content-Disposition':'attachment; filename="crawlinsight-books.csv"','Cache-Control':'no-store'})
