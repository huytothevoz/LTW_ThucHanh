"""CrawlInsight | bilingual personalized web crawling workspace.
Runs as a local Flask server; never serve project files using XAMPP Apache.
"""
from __future__ import annotations
import os
import secrets
import subprocess
import sys
from datetime import timedelta
from pathlib import Path
from flask import Flask,g,jsonify,render_template,request,session,redirect
from src import db
from src.database import accounts as accounts
from src.i18n import translate
from src.web.security import api_error,csrf_token,csrf_valid,require_login
from src.web.auth import auth
from src.web.workspace import workspace

ROOT=Path(__file__).resolve().parent


def load_local_config(path: Path) -> None:
    """Read opt-in .env config, ignoring unknown keys; never run shell code."""
    allowed={'FLASK_HOST','FLASK_PORT','CRAWLINSIGHT_DB_PATH','CRAWLINSIGHT_SECRET_KEY',
        'CRAWLINSIGHT_HTTPS','SMTP_HOST','SMTP_PORT','SMTP_FROM','SMTP_USER',
        'SMTP_PASSWORD','ALLOW_LOCAL_RESET_LINKS'}
    if not path.is_file():return
    for raw in path.read_text(encoding='utf-8-sig').splitlines():
        entry=raw.strip()
        if not entry or entry.startswith('#') or '=' not in entry:continue
        k,v=entry.split('=',1);k=k.strip();v=v.strip()
        if k not in allowed:continue
        if len(v)>=2 and v[0]==v[-1] and v[0] in ('"',"'"):v=v[1:-1]
        os.environ.setdefault(k,v)

load_local_config(ROOT/'.env')


def local_secret():
    configured=os.getenv('CRAWLINSIGHT_SECRET_KEY')
    if configured:
        if len(configured)<32:raise RuntimeError('CRAWLINSIGHT_SECRET_KEY must be >=32 characters')
        return configured
    # Stable across local app restarts and located outside htdocs if applicable.
    path=db.database_path().parent/'flask-session.key'
    path.parent.mkdir(parents=True,exist_ok=True)
    if not path.exists():
        try:
            with path.open('x',encoding='utf-8') as fh:fh.write(secrets.token_urlsafe(64))
        except FileExistsError:pass
    return path.read_text(encoding='utf-8').strip()

app=Flask(__name__)
app.config.update(SECRET_KEY=local_secret(),JSON_AS_ASCII=False,JSON_SORT_KEYS=False,
  SESSION_COOKIE_HTTPONLY=True,SESSION_COOKIE_SAMESITE='Lax',
  TRUSTED_HOSTS=['127.0.0.1','localhost'],
  SESSION_COOKIE_SECURE=os.getenv('CRAWLINSIGHT_HTTPS')=='1',
  PERMANENT_SESSION_LIFETIME=timedelta(days=7),MAX_CONTENT_LENGTH=16384)
app.json.ensure_ascii=False
app.register_blueprint(auth)
app.register_blueprint(workspace)

# Upgrade is additive and idempotent. Tests override CRAWLINSIGHT_DB_PATH and call init_db.
db.init_db()

@app.before_request
def identity_and_protection():
    # Explicit public static; block incidental files under a source directory.
    g.user=accounts.get_user(session.get('user_id')) if isinstance(session.get('user_id'),int) else None
    if session.get('user_id') and (g.user is None or session.get('session_version') != accounts.session_version(session['user_id'])):
        session.clear();g.user=None
    g.preferences=accounts.get_preferences(g.user['id']) if g.user else {'locale':'en' if (request.args.get('lang') or request.cookies.get('ci_guest_lang'))=='en' else 'vi','theme':'system','book_layout':'grid'}
    g.locale=g.preferences['locale']
    csrf_token()
    if request.method in {'POST','PUT','PATCH','DELETE'}:
        if not csrf_valid(): return api_error('INVALID_CSRF','Phiên bảo mật không hợp lệ. Vui lòng tải lại trang.',403)

@app.context_processor
def template_context():
    return {'user':g.get('user'),'prefs':g.get('preferences',{}),'locale':g.get('locale','vi'),
            't':lambda key:translate(key,g.get('locale','vi')),'csrf':csrf_token()}

@app.after_request
def security_headers(response):
    response.headers['X-Content-Type-Options']='nosniff'
    response.headers['Referrer-Policy']='strict-origin-when-cross-origin'
    response.headers['X-Frame-Options']='DENY'
    response.headers['Content-Security-Policy']=("default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' https://books.toscrape.com data:; "
        "font-src 'self'; connect-src 'self'; form-action 'self'; object-src 'none'; base-uri 'self'; frame-ancestors 'none'")
    if request.args.get('lang') in ('vi','en') and g.get('user') is None:
        response.set_cookie('ci_guest_lang',request.args['lang'],max_age=31536000,secure=app.config['SESSION_COOKIE_SECURE'],httponly=False,samesite='Lax')
    if request.path.startswith('/api/') or request.path.startswith('/reset-password'):
        response.headers['Cache-Control']='no-store'
    return response

@app.get('/')
def index_page():
    return render_template('index.html',active_page=None)

@app.get('/api/health')
def health_endpoint():
    return jsonify({'status':'ok','app':'CrawlInsight','database':'sqlite'})

@app.post('/api/jobs')
@require_login
def create_job_endpoint():
    payload=request.get_json(silent=True)
    if not isinstance(payload,dict) or set(payload)!={'max_pages'} or type(payload['max_pages']) is not int or payload['max_pages'] not in (1,2,3):
        return api_error('INVALID_MAX_PAGES','max_pages phải là số nguyên từ 1 đến 3.',400)
    try:
        job=db.create_job(payload['max_pages'])
    except db.ActiveJobError:
        return api_error('JOB_ALREADY_ACTIVE','Đang có lượt crawl khác hoạt động.',409)
    with db.connect() as con:
        con.execute('UPDATE crawl_jobs SET user_id=? WHERE id=?',(g.user['id'],job['id']))
    log_dir=db.database_path().parent/'logs';log_dir.mkdir(parents=True,exist_ok=True)
    try:
        with (log_dir/f'crawl-job-{job["id"]}.log').open('a',encoding='utf-8') as fh:
            subprocess.Popen([sys.executable,'-m','crawler.run_job','--job-id',str(job['id'])],
                cwd=str(ROOT),stdin=subprocess.DEVNULL,stdout=fh,stderr=subprocess.STDOUT,
                shell=False,close_fds=True)
    except OSError:
        db.finish_job(job['id'],'FAILED','Crawler process could not start')
        return api_error('CRAWLER_LAUNCH_FAILED','Không khởi chạy được crawler.',503)
    return jsonify({'job':{'id':job['id'],'status':'PENDING','max_pages':job['max_pages'],'created_at':job['created_at']}}),202

@app.get('/api/jobs/<int:job_id>')
@require_login
def get_job_endpoint(job_id):
    job=db.get_job(job_id)
    if not job or job['user_id']!=g.user['id']:
        return api_error('JOB_NOT_FOUND','Không tìm thấy lượt crawl.',404)
    return jsonify({'job':job,'events':db.list_job_events(job_id,30)})

@app.errorhandler(404)
def not_found(_):
    if request.path.startswith('/api/'):return api_error('NOT_FOUND','Đường dẫn API không tồn tại.',404)
    return render_template('404.html',active_page=None),404

@app.errorhandler(500)
def server_error(_):
    if request.path.startswith('/api/'):return api_error('INTERNAL_ERROR','Lỗi máy chủ. Vui lòng thử lại.',500)
    return render_template('500.html',active_page=None),500

if __name__=='__main__':
    host=os.getenv('FLASK_HOST','127.0.0.1')
    if host not in ('127.0.0.1','localhost'):
        raise SystemExit('Local-only: FLASK_HOST must be 127.0.0.1')
    port=int(os.getenv('FLASK_PORT','5000'))
    app.run(host='127.0.0.1',port=port,debug=False,use_reloader=False)
