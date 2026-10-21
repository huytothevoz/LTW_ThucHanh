"""Authentication pages and APIs; Flask signed session, CSRF, time-limited reset tokens."""
from __future__ import annotations
import os
from urllib.parse import urljoin
from flask import Blueprint, current_app, g, jsonify, redirect, render_template, request, session, url_for
from src.database import accounts as a
from src.web.security import api_error,csrf_token,require_login
from src.web.mail import send_reset,smtp_ready

auth=Blueprint('auth',__name__)


def _json():
    data=request.get_json(silent=True)
    return data if isinstance(data,dict) else {}


def _login(user):
    session.clear()  # new session + CSRF after authentication
    session['user_id']=user['id']
    session['session_version']=a.session_version(user['id'])
    session.permanent=True
    csrf_token()


@auth.get('/login')
def login_page():
    if g.user: return redirect('/workspace')
    return render_template('auth.html',mode='login',active_page=None)


@auth.get('/register')
def register_page():
    if g.user: return redirect('/workspace')
    return render_template('auth.html',mode='register',active_page=None)


@auth.get('/forgot-password')
def forgot_page():
    return render_template('auth.html',mode='forgot',active_page=None)


@auth.get('/reset-password/<token>')
def reset_page(token):
    return render_template('auth.html',mode='reset',reset_token=token,active_page=None)


@auth.get('/api/auth/me')
def whoami():
    return jsonify({'user':g.user,'preferences':a.get_preferences(g.user['id']) if g.user else None})


@auth.post('/api/auth/register')
def register_api():
    d=_json()
    try: user=a.register(d.get('full_name',''),d.get('email',''),d.get('password',''))
    except a.AccountError as e: return api_error('VALIDATION_ERROR',str(e),400)
    _login(user)
    return jsonify({'user':user,'preferences':a.get_preferences(user['id'])}),201


@auth.post('/api/auth/login')
def login_api():
    d=_json();mail=str(d.get('email','')).strip().lower()[:254]
    subject='login:'+mail+':'+str(request.remote_addr or 'local')
    if a.rate_limited(subject,7,15):return api_error('TOO_MANY_ATTEMPTS','Thử lại sau 15 phút.',429)
    user=a.authenticate(mail,d.get('password',''))
    a.record_auth_attempt(subject, bool(user))
    if not user: return api_error('INVALID_CREDENTIALS','Email hoặc mật khẩu không chính xác.',401)
    _login(user)
    return jsonify({'user':user,'preferences':a.get_preferences(user['id'])})


@auth.post('/api/auth/logout')
@require_login
def logout_api():
    session.clear()
    return jsonify({'ok':True})


@auth.post('/api/auth/request-reset')
def request_reset_api():
    d=_json();mail=str(d.get('email','')).strip().lower()[:254]
    # Counter repeated requests even for nonexistent addresses; prevents enumeration.
    subject='reset:'+mail+':'+str(request.remote_addr or 'local')
    if a.rate_limited(subject,4,30):return api_error('TOO_MANY_ATTEMPTS','Thử lại sau 30 phút.',429)
    if not smtp_ready() and not (current_app.config.get('TESTING') or
            (os.getenv('ALLOW_LOCAL_RESET_LINKS')=='1' and request.remote_addr in ('127.0.0.1','::1'))):
        return api_error('MAIL_NOT_CONFIGURED','Máy chủ chưa cấu hình email SMTP. Hãy liên hệ quản trị viên.',503)
    a.record_auth_attempt(subject,False)
    result=a.create_reset_token(mail)
    response={'message':'Nếu email đã tồn tại, bạn sẽ nhận được hướng dẫn khôi phục.'}
    if result:
        token,user=result
        link=url_for('auth.reset_page',token=token,_external=True)
        if smtp_ready():
            try:send_reset(user['email'],user['full_name'],link,g.locale)
            except Exception:
                current_app.logger.exception('SMTP delivery failed')
                return api_error('EMAIL_DELIVERY_FAILED','Không thể gửi email. Vui lòng kiểm tra lại cấu hình SMTP.',503)
        elif current_app.config.get('TESTING') or (os.getenv('ALLOW_LOCAL_RESET_LINKS')=='1' and request.remote_addr in ('127.0.0.1','::1')):
            response['local_test_link']=link # Strictly local opt-in; never on public deployment
    return jsonify(response)


@auth.post('/api/auth/reset-password')
def reset_password_api():
    d=_json()
    try:ok=a.reset_password(d.get('token',''),d.get('password',''))
    except a.AccountError as e:return api_error('VALIDATION_ERROR',str(e),400)
    if not ok:return api_error('INVALID_TOKEN','Liên kết không hợp lệ, đã sử dụng hoặc hết hạn.',400)
    session.clear()
    return jsonify({'ok':True})


@auth.patch('/api/me/profile')
@require_login
def update_profile():
    try:user=a.update_profile(g.user['id'],_json().get('full_name',''))
    except a.AccountError as e:return api_error('VALIDATION_ERROR',str(e),400)
    return jsonify({'user':user})


@auth.patch('/api/me/preferences')
@require_login
def update_preferences():
    try:prefs=a.update_preferences(g.user['id'],_json())
    except a.AccountError as e:return api_error('VALIDATION_ERROR',str(e),400)
    return jsonify({'preferences':prefs})


@auth.post('/api/me/password')
@require_login
def update_password():
    d=_json()
    try:a.change_password(g.user['id'],d.get('current_password',''),d.get('new_password',''))
    except a.AccountError as e:return api_error('VALIDATION_ERROR',str(e),400)
    session.clear() # force re-login after sensitive credential change
    return jsonify({'ok':True,'reauth_required':True})
