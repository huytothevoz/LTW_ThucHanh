"""Identity & workspace tests independent of Flask/Scrapy; run on bare Python."""
from __future__ import annotations
import hashlib
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path
import pytest
from src import db
from src.database import accounts as a


def user(email='duy@example.com', name='Nguyễn Minh Duy'):
    return a.register(name,email,'abcDEF12345!')


def create_book(example_book):
    job=db.create_job(1)
    db.mark_job_running(job['id']);db.save_book_for_job(job['id'],example_book)
    db.finish_job(job['id'],'COMPLETED')
    return db.search_books()['items'][0]['id']


def test_migration_v4_creates_user_tables_empty_and_integrity(isolated_db):
    with db.connect() as con:
        names={r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        assert {'users','user_preferences','bookmarks','saved_searches','password_reset_tokens','auth_attempts'}<=names
        assert {r[0] for r in con.execute('SELECT version FROM schema_migrations')}=={1,2,3,4}
        assert con.execute('SELECT COUNT(*) FROM users').fetchone()[0]==0
        assert any(r['name']=='user_id' for r in con.execute('PRAGMA table_info(crawl_jobs)'))
        assert con.execute('PRAGMA foreign_key_check').fetchall()==[]


def test_registration_hash_is_salted_not_plaintext(isolated_db):
    first=user();second=user('quy@example.com','Nguyễn Trọng Quý')
    assert first['id']!=second['id']
    with db.connect() as con:
        data=con.execute('SELECT password_hash FROM users ORDER BY id').fetchall()
        assert data[0][0]!=data[1][0]
        assert 'abcDEF12345!' not in data[0][0]
        assert data[0][0].startswith('scrypt:')
    assert a.authenticate('DUY@example.com','abcDEF12345!')['id']==first['id']
    assert a.authenticate('duy@example.com','incorrect') is None
    assert a.get_preferences(first['id'])=={'locale':'vi','theme':'system','book_layout':'grid'}


def test_reject_invalid_registration_and_duplicate_emails(isolated_db):
    for name, email, passwd in [('A','a@example.com','abcDEF12345!'),('Nguyen','not-email','abcDEF12345!'),('Nguyen','n@example.com','short'),('Nguyen','n@example.com','012345678910')]:
        with pytest.raises(a.AccountError):a.register(name,email,passwd)
    user()
    with pytest.raises(a.AccountError):a.register('Người khác','DUY@example.com','abcDEF12345!')


def test_prefs_update_only_allowed_keys_values(isolated_db):
    u=user();uid=u['id']
    assert a.update_preferences(uid,{'locale':'en','theme':'dark','book_layout':'list'})=={'locale':'en','theme':'dark','book_layout':'list'}
    for data in ({},{'theme':'purple'},{'is_admin':True},{'theme':False}):
        with pytest.raises(a.AccountError):a.update_preferences(uid,data)
    assert a.update_profile(uid,'  Phạm    Ngọc   Duy ')['full_name']=='Phạm Ngọc Duy'


def test_bookmarks_are_personal_with_fk_cleanup(isolated_db,example_book):
    d=user();q=user('quy@example.com','Nguyễn Trọng Quý')
    bid=create_book(example_book)
    assert a.add_bookmark(d['id'],bid)=={'book_id':bid,'saved':True}
    assert a.add_bookmark(d['id'],bid)=={'book_id':bid,'saved':True}
    assert a.list_bookmarks(d['id'])['total']==1
    assert a.list_bookmarks(q['id'])['total']==0
    assert a.bookmark_ids(d['id'],[bid])==[bid]
    assert a.bookmark_ids(q['id'],[bid])==[]
    a.remove_bookmark(q['id'],bid)
    assert a.list_bookmarks(d['id'])['total']==1
    with db.connect() as con:
        assert con.execute('SELECT COUNT(*) FROM bookmarks').fetchone()[0]==1
        con.execute('DELETE FROM users WHERE id=?',(d['id'],))
        assert con.execute('SELECT COUNT(*) FROM bookmarks').fetchone()[0]==0
        assert con.execute('SELECT COUNT(*) FROM books').fetchone()[0]==1


def test_saved_search_isolation_validation_and_delete(isolated_db):
    d=user();q=user('quy@example.com','Nguyễn Trọng Quý')
    item=a.save_search(d['id'],'Lọc sách rẻ','Python','5.25','32.50')
    assert a.list_searches(d['id'])[0]['name']=='Lọc sách rẻ'
    assert a.list_searches(q['id'])==[]
    assert a.delete_search(q['id'],item['id']) is False
    with pytest.raises(ValueError):a.save_search(d['id'],'Bad','test','80','20')
    assert a.delete_search(d['id'],item['id']) is True


def test_reset_token_one_time_only_and_session_revocation(isolated_db):
    u=user()
    before=a.session_version(u['id'])
    result=a.create_reset_token('duy@example.com')
    assert result is not None
    token,_=result
    with db.connect() as con:
        row=con.execute('SELECT token_hash FROM password_reset_tokens').fetchone()
        assert row['token_hash']==hashlib.sha256(token.encode()).hexdigest()
        assert token not in row['token_hash']
    assert a.reset_password('invalid token', 'AnotherPass123') is False
    assert a.reset_password(token,'AnotherPass123') is True
    assert a.reset_password(token,'ThirdPass456') is False
    assert a.authenticate('duy@example.com','abcDEF12345!') is None
    assert a.authenticate('duy@example.com','AnotherPass123') is not None
    assert a.session_version(u['id'])==before+1


def test_reset_token_expired_and_invalidates_older_tokens(isolated_db):
    u=user();first=a.create_reset_token('duy@example.com')[0]
    second=a.create_reset_token('duy@example.com')[0]
    assert a.reset_password(first,'AnotherPass123') is False
    with db.connect() as con:
        con.execute('UPDATE password_reset_tokens SET expires_at=? WHERE token_hash=?',('2020-01-01T00:00:00Z',hashlib.sha256(second.encode()).hexdigest()))
    assert a.reset_password(second,'AnotherPass123') is False
    assert a.create_reset_token('doesnotexist@example.com') is None


def test_change_password_checks_old_secret_and_revokes_sessions(isolated_db):
    u=user()
    with pytest.raises(a.AccountError):a.change_password(u['id'],'bad','SecurePass123')
    v=a.session_version(u['id'])
    a.change_password(u['id'],'abcDEF12345!','SecurePass123')
    assert a.session_version(u['id'])==v+1
    assert a.authenticate('duy@example.com','SecurePass123') is not None


def test_auth_rate_tracking_is_hashed(isolated_db):
    key='login:duy@example.com:127.0.0.1'
    assert not a.rate_limited(key,3,15)
    for _ in range(3):a.record_auth_attempt(key,False)
    assert a.rate_limited(key,3,15)
    with db.connect() as con:
        rows=con.execute('SELECT subject_hash FROM auth_attempts').fetchall()
        assert all('duy' not in r[0] for r in rows)


def test_crawl_job_user_id_nullable_for_legacy(isolated_db):
    user_id=user()['id']
    job=db.create_job(1)
    with db.connect() as con:
        assert con.execute('SELECT user_id FROM crawl_jobs WHERE id=?',(job['id'],)).fetchone()[0] is None
        con.execute('UPDATE crawl_jobs SET user_id=? WHERE id=?',(user_id,job['id']))
        assert con.execute('SELECT user_id FROM crawl_jobs WHERE id=?',(job['id'],)).fetchone()[0]==user_id
        with pytest.raises(sqlite3.IntegrityError):con.execute('UPDATE crawl_jobs SET user_id=99999 WHERE id=?',(job['id'],))
    db.finish_job(job['id'],'FAILED')


def test_upgrade_existing_v3_database_preserves_data(tmp_path,monkeypatch):
    from src.database.connection import MIGRATIONS_DIR
    path=tmp_path/'v3-old.sqlite3'
    with sqlite3.connect(path) as con:
        con.executescript((MIGRATIONS_DIR/'001_core.sql').read_text(encoding='utf8'))
        con.execute("INSERT INTO sources(id,name,base_url,allowed_host,created_at) VALUES(1,'Books to Scrape','https://books.toscrape.com/','books.toscrape.com','2026-01-01T00:00:00Z')")
        con.executescript((MIGRATIONS_DIR/'002_indexes.sql').read_text(encoding='utf8'))
        con.executescript((MIGRATIONS_DIR/'003_views.sql').read_text(encoding='utf8'))
        for v in (1,2,3):con.execute('INSERT INTO schema_migrations(version,filename,applied_at) VALUES(?,?,?)',(v,f'{v:03}_old.sql','2026-01-01T00:00:00Z'))
        con.execute("INSERT INTO categories(source_id,name,first_seen_at) VALUES(1,'History','2026-01-01T00:00:00Z')")
        con.execute("INSERT INTO books(source_id,category_id,source_url,title,price_pence,rating,availability,first_seen_at,last_seen_at) VALUES(1,1,'https://books.toscrape.com/catalogue/kept_1/index.html','Keep This Book',1200,4,'In stock','2026-01-01T00:00:00Z','2026-01-01T00:00:00Z')")
    monkeypatch.setenv('CRAWLINSIGHT_DB_PATH',str(path))
    db.init_db()
    with db.connect() as con:
        assert con.execute('SELECT title FROM books').fetchone()[0]=='Keep This Book'
        assert con.execute('SELECT COUNT(*) FROM users').fetchone()[0]==0
        assert {r[0] for r in con.execute('SELECT version FROM schema_migrations')}=={1,2,3,4}
        assert con.execute('PRAGMA integrity_check').fetchone()[0]=='ok'
    backups=list(tmp_path.glob('v3-old.before-v4-*.sqlite3'))
    assert len(backups)==1
    with sqlite3.connect(backups[0]) as con:
        assert con.execute('SELECT title FROM books').fetchone()[0]=='Keep This Book'
        assert con.execute("SELECT name FROM sqlite_master WHERE name='users'").fetchone() is None
    db.init_db()
    assert len(list(tmp_path.glob('v3-old.before-v4-*.sqlite3')))==1
