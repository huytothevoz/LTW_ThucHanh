"""Session and CSRF guards shared by all blueprints."""
import secrets
from functools import wraps
from flask import g, jsonify, redirect, request, session, url_for


def csrf_token():
    if 'csrf' not in session:session['csrf']=secrets.token_urlsafe(32)
    return session['csrf']


def csrf_valid():
    token=request.headers.get('X-CSRF-Token','')
    return bool(token and secrets.compare_digest(token,session.get('csrf','')))


def require_login(view):
    @wraps(view)
    def wrapped(*args,**kwargs):
        if g.user is None:
            if request.path.startswith('/api/'):
                return jsonify({'error':{'code':'AUTH_REQUIRED','message':'Vui lòng đăng nhập để tiếp tục.'}}),401
            return redirect(url_for('auth.login_page',next=request.path))
        return view(*args,**kwargs)
    return wrapped


def api_error(code,msg,status):
    return jsonify({'error':{'code':code,'message':msg}}),status
