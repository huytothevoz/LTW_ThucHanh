"""Persistent user identity, per-user preferences, bookmarks and recovery tokens.
No SQL lives in route handlers. Password hashes are Werkzeug salted scrypt.
"""
from __future__ import annotations
import hashlib
import hmac
import os
import re
import secrets
from datetime import datetime, timedelta, timezone
from .connection import connect, now_utc
from .books import parse_price_filter

EMAIL = re.compile(r"^[A-Z0-9._%+\-]+@[A-Z0-9.\-]+\.[A-Z]{2,}$", re.I)

class AccountError(ValueError):
    pass


def generate_password_hash(password: str, method: str='scrypt') -> str:
    """Password verifier built with stdlib scrypt (random 16-byte salt)."""
    salt=os.urandom(16)
    hashed=hashlib.scrypt(password.encode('utf-8'),salt=salt,n=2**14,r=8,p=1,dklen=64)
    return f'scrypt:16384:8:1${salt.hex()}${hashed.hex()}'


def check_password_hash(stored: str, password: str) -> bool:
    try:
        method,salt,expected=stored.split('$')
        if method!='scrypt:16384:8:1':return False
        actual=hashlib.scrypt(password.encode('utf-8'),salt=bytes.fromhex(salt),n=2**14,r=8,p=1,dklen=64)
        return hmac.compare_digest(actual,bytes.fromhex(expected))
    except (ValueError,TypeError,AttributeError):return False


def _public_user(row):
    if row is None: return None
    return {k: row[k] for k in ('id', 'full_name', 'email', 'created_at', 'last_login_at', 'is_active')}


def register(full_name: str, email: str, password: str) -> dict:
    name = ' '.join(str(full_name).split())
    mail = str(email).strip().lower()
    if not 2 <= len(name) <= 100: raise AccountError('Tên phải dài từ 2 đến 100 ký tự.')
    if len(mail)>254 or not EMAIL.fullmatch(mail): raise AccountError('Email không hợp lệ.')
    _check_password(password)
    hashed = generate_password_hash(password, method='scrypt')
    now = now_utc()
    with connect() as con:
        con.execute('BEGIN IMMEDIATE')
        if con.execute('SELECT id FROM users WHERE email=?', (mail,)).fetchone():
            raise AccountError('Email này đã được đăng ký.')
        cur = con.execute('INSERT INTO users(full_name,email,password_hash,created_at,updated_at) VALUES(?,?,?,?,?)', (name,mail,hashed,now,now))
        con.execute('INSERT INTO user_preferences(user_id,locale,theme,book_layout,updated_at) VALUES(?,?,?,?,?)', (cur.lastrowid,'vi','system','grid',now))
        return _public_user(con.execute('SELECT * FROM users WHERE id=?',(cur.lastrowid,)).fetchone())


def _check_password(password):
    if not isinstance(password,str) or not 10 <= len(password) <= 128 or not re.search(r'[A-Za-z]',password) or not re.search(r'\d',password):
        raise AccountError('Mật khẩu cần 10–128 ký tự, có chữ cái và số.')


def session_version(user_id: int) -> int | None:
    with connect() as con:
        row=con.execute('SELECT session_version FROM users WHERE id=? AND is_active=1',(user_id,)).fetchone()
        return int(row['session_version']) if row else None


def get_user(user_id: int) -> dict | None:
    with connect() as con:
        return _public_user(con.execute('SELECT * FROM users WHERE id=? AND is_active=1',(user_id,)).fetchone())


def authenticate(email: str, password: str) -> dict | None:
    mail = str(email).strip().lower()[:254]
    with connect() as con:
        row=con.execute('SELECT * FROM users WHERE email=? AND is_active=1',(mail,)).fetchone()
        if not row or not isinstance(password,str) or not check_password_hash(row['password_hash'], password):
            return None
        con.execute('UPDATE users SET last_login_at=? WHERE id=?',(now_utc(),row['id']))
        return _public_user(row)


def get_preferences(user_id: int) -> dict:
    with connect() as con:
        row=con.execute('SELECT locale,theme,book_layout FROM user_preferences WHERE user_id=?',(user_id,)).fetchone()
        return dict(row) if row else {'locale':'vi','theme':'system','book_layout':'grid'}


def update_preferences(user_id: int, values: dict) -> dict:
    allowed={'locale':('vi','en'),'theme':('light','dark','system'),'book_layout':('grid','list')}
    if not isinstance(values,dict) or not values or set(values)-set(allowed):
        raise AccountError('Cấu hình không hợp lệ.')
    for k,v in values.items():
        if type(v) is not str or v not in allowed[k]: raise AccountError(f'Giá trị {k} không hợp lệ.')
    with connect() as con:
        for key,val in values.items():
            con.execute(f'UPDATE user_preferences SET {key}=?,updated_at=? WHERE user_id=?',(val,now_utc(),user_id))
    return get_preferences(user_id)


def update_profile(user_id: int, name: str) -> dict:
    cleaned=' '.join(str(name).split())
    if not 2<=len(cleaned)<=100: raise AccountError('Tên phải dài từ 2 đến 100 ký tự.')
    with connect() as con:
        con.execute('UPDATE users SET full_name=?,updated_at=? WHERE id=?',(cleaned,now_utc(),user_id))
    return get_user(user_id)


def change_password(user_id: int, current: str, next_password: str):
    _check_password(next_password)
    with connect() as con:
        con.execute('BEGIN IMMEDIATE')
        row=con.execute('SELECT password_hash FROM users WHERE id=?',(user_id,)).fetchone()
        if not row or not check_password_hash(row['password_hash'], current):
            raise AccountError('Mật khẩu hiện tại không đúng.')
        con.execute('UPDATE users SET password_hash=?,session_version=session_version+1,updated_at=? WHERE id=?',(generate_password_hash(next_password,method='scrypt'),now_utc(),user_id))
        con.execute('UPDATE password_reset_tokens SET used_at=? WHERE user_id=? AND used_at IS NULL',(now_utc(),user_id))


def create_reset_token(email: str) -> tuple[str,dict] | None:
    mail=str(email).strip().lower()
    with connect() as con:
        con.execute('BEGIN IMMEDIATE')
        row=con.execute('SELECT * FROM users WHERE email=? AND is_active=1',(mail,)).fetchone()
        if not row: return None
        token=secrets.token_urlsafe(36)
        digest=hashlib.sha256(token.encode()).hexdigest()
        expiry=(datetime.now(timezone.utc)+timedelta(minutes=20)).strftime('%Y-%m-%dT%H:%M:%SZ')
        con.execute('UPDATE password_reset_tokens SET used_at=? WHERE user_id=? AND used_at IS NULL',(now_utc(),row['id']))
        con.execute('INSERT INTO password_reset_tokens(user_id,token_hash,expires_at,created_at) VALUES(?,?,?,?)',(row['id'],digest,expiry,now_utc()))
        return token,_public_user(row)


def reset_password(token: str, new_password: str) -> bool:
    _check_password(new_password)
    if not isinstance(token,str) or not 24<=len(token)<=200: return False
    digest=hashlib.sha256(token.encode()).hexdigest()
    with connect() as con:
        con.execute('BEGIN IMMEDIATE')
        row=con.execute('SELECT id,user_id,expires_at,used_at FROM password_reset_tokens WHERE token_hash=?',(digest,)).fetchone()
        if not row or row['used_at'] or row['expires_at']<=now_utc(): return False
        con.execute('UPDATE users SET password_hash=?,session_version=session_version+1,updated_at=? WHERE id=?',(generate_password_hash(new_password,method='scrypt'),now_utc(),row['user_id']))
        con.execute('UPDATE password_reset_tokens SET used_at=? WHERE user_id=? AND used_at IS NULL',(now_utc(),row['user_id']))
    return True


def add_bookmark(user_id: int, book_id: int) -> dict | None:
    with connect() as con:
        con.execute('BEGIN IMMEDIATE')
        if not con.execute('SELECT id FROM books WHERE id=?',(book_id,)).fetchone(): return None
        con.execute('INSERT OR IGNORE INTO bookmarks(user_id,book_id,created_at) VALUES(?,?,?)',(user_id,book_id,now_utc()))
        return {'book_id':book_id,'saved':True}


def remove_bookmark(user_id: int, book_id: int) -> dict:
    with connect() as con:
        con.execute('DELETE FROM bookmarks WHERE user_id=? AND book_id=?',(user_id,book_id))
    return {'book_id':book_id,'saved':False}


def list_bookmarks(user_id: int, page=1) -> dict:
    if type(page) is not int or page<1: raise AccountError('Trang không hợp lệ.')
    with connect() as con:
        total=con.execute('SELECT COUNT(*) FROM bookmarks WHERE user_id=?',(user_id,)).fetchone()[0]
        rows=con.execute('''SELECT b.id,b.title,b.price_pence,b.rating,b.availability,b.source_url,b.image_url,c.name category,
              bk.note,bk.created_at AS bookmarked_at FROM bookmarks bk JOIN books b ON b.id=bk.book_id
              JOIN categories c ON b.category_id=c.id WHERE bk.user_id=? ORDER BY bk.created_at DESC,bk.id DESC LIMIT 12 OFFSET ?''',(user_id,(page-1)*12)).fetchall()
    return {'items':[dict(r) for r in rows], 'total':total, 'page':page, 'page_size':12, 'total_pages':(total+11)//12}


def bookmark_ids(user_id:int, ids:list[int]) -> list[int]:
    if not ids:return []
    marks=','.join('?' for _ in ids)
    with connect() as con:
        return [int(r[0]) for r in con.execute(f'SELECT book_id FROM bookmarks WHERE user_id=? AND book_id IN ({marks})',[user_id,*ids])]


def save_search(user_id:int, name:str, q:str, low:str, high:str):
    name=' '.join(str(name).split())
    if not 1<=len(name)<=60 or len(q)>100: raise AccountError('Tên bộ lọc hoặc từ khóa quá dài.')
    lp=parse_price_filter(low,'min_price');hp=parse_price_filter(high,'max_price')
    if lp is not None and hp is not None and lp>hp: raise AccountError('Khoảng giá không hợp lệ.')
    with connect() as con:
        con.execute('BEGIN IMMEDIATE')
        if con.execute('SELECT COUNT(*) FROM saved_searches WHERE user_id=?',(user_id,)).fetchone()[0]>=20:
            raise AccountError('Tối đa 20 bộ lọc đã lưu.')
        cur=con.execute('INSERT INTO saved_searches(user_id,name,query,min_price,max_price,created_at) VALUES(?,?,?,?,?,?)',
            (user_id,name,q,low or '',high or '',now_utc()))
        return {'id':cur.lastrowid,'name':name}


def list_searches(user_id:int):
    with connect() as con:
        return [dict(r) for r in con.execute('SELECT id,name,query,min_price,max_price,created_at FROM saved_searches WHERE user_id=? ORDER BY id DESC',(user_id,))]


def delete_search(user_id:int, search_id:int):
    with connect() as con:
        return con.execute('DELETE FROM saved_searches WHERE id=? AND user_id=?',(search_id,user_id)).rowcount>0


def rate_limited(subject: str, max_attempts: int, minutes: int) -> bool:
    hashed=hashlib.sha256(subject.encode()).hexdigest()
    cutoff=(datetime.now(timezone.utc)-timedelta(minutes=minutes)).strftime('%Y-%m-%dT%H:%M:%SZ')
    with connect() as con:
        total=con.execute('SELECT COUNT(*) FROM auth_attempts WHERE subject_hash=? AND attempted_at>? AND success=0',(hashed,cutoff)).fetchone()[0]
        return total>=max_attempts


def record_auth_attempt(subject: str, success: bool):
    hashed=hashlib.sha256(subject.encode()).hexdigest()
    with connect() as con:
        con.execute('INSERT INTO auth_attempts(subject_hash,attempted_at,success) VALUES(?,?,?)',(hashed,now_utc(),int(success)))
        con.execute('DELETE FROM auth_attempts WHERE attempted_at < ?',((datetime.now(timezone.utc)-timedelta(days=2)).strftime('%Y-%m-%dT%H:%M:%SZ'),))
