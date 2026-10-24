"""New schema relationships, audit behavior, migration, demo isolation, CLI."""
from __future__ import annotations
import os
import sqlite3
from pathlib import Path
import pytest
from src import db
from src.database import migrations
from database.tools.sqlite_legacy import open_ro,seed_demo,rows_of


def test_tables_views_and_empty_initial_state(isolated_db):
    with db.connect() as con:
        tables={r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        assert {'sources','categories','books','crawl_jobs','crawl_pages','crawl_job_books','crawl_events','book_price_history','price_change_notifications','schema_migrations'} <= tables
        assert con.execute('SELECT COUNT(*) FROM sources').fetchone()[0]==1
        for name in ('books','categories','crawl_jobs','crawl_pages','crawl_events','book_price_history','price_change_notifications'):
            assert con.execute(f'SELECT COUNT(*) FROM {name}').fetchone()[0]==0
        assert con.execute('PRAGMA integrity_check').fetchone()[0]=='ok'
        assert con.execute('PRAGMA foreign_key_check').fetchall()==[]
        assert {r[0] for r in con.execute('SELECT version FROM schema_migrations')}=={1,2,3,4,5,6}
    db.init_db()  # idempotent, no duplicate source
    with db.connect() as con:
        assert con.execute('SELECT COUNT(*) FROM sources').fetchone()[0]==1


def test_normalization_page_evidence_and_views(isolated_db,example_book):
    j=db.create_job(2);db.mark_job_running(j['id'])
    url='https://books.toscrape.com/'
    db.record_catalogue_page(j['id'],url,1,1)
    db.record_catalogue_page(j['id'],url,1,1) # no double counting
    assert db.save_book_for_job(j['id'],example_book)=='new'
    assert db.save_book_for_job(j['id'],example_book)=='existing' # no duplicate counter
    assert db.get_job(j['id'])['items_saved']==1
    assert db.get_job(j['id'])['catalogue_pages_done']==1
    assert db.get_job(j['id'])['books_found']==1
    with db.connect() as con:
        assert con.execute('SELECT COUNT(*) FROM categories').fetchone()[0]==1
        assert con.execute('SELECT category FROM v_books_detail').fetchone()[0]=='Science'
        assert con.execute('SELECT total_books FROM v_category_summary').fetchone()[0]==1
        assert con.execute('SELECT action FROM crawl_job_books').fetchone()[0]=='NEW'
        assert con.execute('SELECT COUNT(*) FROM crawl_events').fetchone()[0]==2
        with pytest.raises(sqlite3.IntegrityError):
            con.execute("INSERT INTO crawl_job_books(job_id,book_id,action,observed_price_pence,observed_rating,observed_at) VALUES(999,1,'NEW',100,5,'2026-01-01T00:00:00Z')")
    db.finish_job(j['id'],'COMPLETED')
    assert db.get_job(j['id'])['status']=='COMPLETED'


def test_price_history_only_changed_and_action_classification(isolated_db,example_book):
    j1=db.create_job(1);db.mark_job_running(j1['id']);db.save_book_for_job(j1['id'],example_book);db.finish_job(j1['id'],'COMPLETED')
    j2=db.create_job(1);db.mark_job_running(j2['id']);db.save_book_for_job(j2['id'],example_book);db.finish_job(j2['id'],'COMPLETED')
    j3=db.create_job(1);db.mark_job_running(j3['id']);db.save_book_for_job(j3['id'],{**example_book,'price_pence':2222,'category':'science'});db.finish_job(j3['id'],'COMPLETED')
    with db.connect() as con:
        assert [r[0] for r in con.execute('SELECT action FROM crawl_job_books ORDER BY id')]==['NEW','UNCHANGED','UPDATED']
        changed=con.execute('SELECT old_price_pence,new_price_pence FROM book_price_history').fetchone()
        assert tuple(changed)==(1234,2222)
        assert con.execute('SELECT COUNT(*) FROM categories').fetchone()[0]==1
        assert con.execute('SELECT COUNT(*) FROM books').fetchone()[0]==1
        assert con.execute('PRAGMA foreign_key_check').fetchall()==[]


def test_price_change_notifies_only_users_who_bookmarked_the_book(isolated_db,example_book):
    with db.connect() as con:
        for email in ('one@example.com','two@example.com'):
            con.execute(
                'INSERT INTO users(full_name,email,password_hash,created_at,updated_at) VALUES(?,?,?,?,?)',
                (email.split('@')[0],email,'test-hash',db.now_utc(),db.now_utc()),
            )

    first_job=db.create_job(1,user_id=1);db.mark_job_running(first_job['id'])
    db.save_book_for_job(first_job['id'],example_book);db.finish_job(first_job['id'],'COMPLETED')
    with db.connect() as con:
        book_id=con.execute('SELECT id FROM books WHERE source_url=?',(example_book['source_url'],)).fetchone()[0]
        users=con.execute('SELECT id FROM users ORDER BY id').fetchall()
        for user in users:
            con.execute(
                'INSERT INTO bookmarks(user_id,book_id,created_at) VALUES(?,?,?)',
                (user['id'],book_id,db.now_utc()),
            )

    unchanged_job=db.create_job(1,user_id=1);db.mark_job_running(unchanged_job['id'])
    db.save_book_for_job(unchanged_job['id'],example_book);db.finish_job(unchanged_job['id'],'COMPLETED')
    changed_job=db.create_job(1,user_id=1);db.mark_job_running(changed_job['id'])
    db.save_book_for_job(changed_job['id'],{**example_book,'price_pence':2222})
    db.finish_job(changed_job['id'],'COMPLETED')

    with db.connect() as con:
        notifications=con.execute(
            'SELECT user_id,book_id,price_history_id FROM price_change_notifications ORDER BY user_id',
        ).fetchall()
        assert len(notifications)==1
        assert {row['user_id'] for row in notifications}=={users[0]['id']}
        assert {row['book_id'] for row in notifications}=={book_id}
        assert len({row['price_history_id'] for row in notifications})==1
        assert con.execute('PRAGMA foreign_key_check').fetchall()==[]


def test_current_database_migration_is_idempotent(isolated_db):
    db.init_db()
    db.init_db()
    with db.connect() as con:
        assert con.execute(
            "SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name='price_change_notifications'",
        ).fetchone()[0]==1
        assert {row[0] for row in con.execute('SELECT version FROM schema_migrations')}=={1,2,3,4,5,6}


def test_users_have_separate_crawl_jobs_and_book_catalogs(isolated_db,example_book):
    with db.connect() as con:
        for user_id in (11,22):
            con.execute(
                'INSERT INTO users(id,full_name,email,password_hash,created_at,updated_at) VALUES(?,?,?,?,?,?)',
                (user_id,f'User {user_id}',f'user{user_id}@example.com','test-hash',db.now_utc(),db.now_utc()),
            )
    first=db.create_job(1,user_id=11)
    second=db.create_job(1,user_id=22)
    db.mark_job_running(first['id'])
    assert db.save_book_for_job(first['id'],example_book)=='new'
    db.finish_job(first['id'],'COMPLETED')

    db.mark_job_running(second['id'])
    assert db.save_book_for_job(second['id'],{**example_book,'price_pence':987})=='new'
    db.finish_job(second['id'],'COMPLETED')

    assert db.search_books(user_id=11)['total']==1
    assert db.search_books(user_id=22)['total']==1
    assert db.search_books(user_id=33)['total']==0
    with db.connect() as con:
        rows=con.execute('SELECT user_id,source_url,price_pence FROM books ORDER BY user_id').fetchall()
        assert [(row['user_id'],row['price_pence']) for row in rows]==[(11,1234),(22,987)]
        assert con.execute('PRAGMA foreign_key_check').fetchall()==[]


def test_v5_migration_splits_shared_books_into_each_owner(tmp_path,monkeypatch,example_book):
    path=tmp_path/'v5.db'
    monkeypatch.setenv('CRAWLINSIGHT_DB_PATH',str(path))
    with sqlite3.connect(path) as con:
        con.executescript((migrations.MIGRATIONS_DIR/'001_core.sql').read_text(encoding='utf8'))
        con.executescript((migrations.MIGRATIONS_DIR/'002_indexes.sql').read_text(encoding='utf8'))
        con.executescript((migrations.MIGRATIONS_DIR/'003_views.sql').read_text(encoding='utf8'))
        con.execute(
            "INSERT INTO sources(id,name,base_url,allowed_host,created_at) VALUES(1,'Books','https://books.toscrape.com/','books.toscrape.com',?)",
            (db.now_utc(),),
        )
        for version,filename in enumerate(migrations.FILES[:3],1):
            con.execute(
                'INSERT INTO schema_migrations(version,filename,applied_at) VALUES(?,?,?)',
                (version,filename,db.now_utc()),
            )
    connection=db.connect()
    try:
        migrations._apply_identity_upgrade(connection)
        migrations._apply_notifications_upgrade(connection)
        now=db.now_utc()
        for user_id in (1,2):
            connection.execute(
                'INSERT INTO users(id,full_name,email,password_hash,created_at,updated_at) VALUES(?,?,?,?,?,?)',
                (user_id,f'User {user_id}',f'user{user_id}@example.com','test-hash',now,now),
            )
        connection.execute(
            "INSERT INTO categories(id,source_id,name,first_seen_at) VALUES(1,1,?,?)",
            (example_book['category'],now),
        )
        jobs=[]
        for user_id in (1,2):
            cursor=connection.execute(
                "INSERT INTO crawl_jobs(source_id,max_pages,status,items_saved,new_books,created_at,finished_at,user_id) "
                "VALUES(1,1,'COMPLETED',1,1,?,?,?)",
                (now,now,user_id),
            )
            jobs.append(cursor.lastrowid)
        connection.execute(
            'INSERT INTO books(id,source_id,category_id,source_url,title,price_pence,rating,availability,first_seen_at,last_seen_at,last_crawl_job_id) '
            "VALUES(1,1,1,?,?,?,?,'In stock',?,?,?)",
            (example_book['source_url'],example_book['title'],example_book['price_pence'],
             example_book['rating'],now,now,jobs[1]),
        )
        connection.execute(
            'INSERT INTO books(id,source_id,category_id,source_url,title,price_pence,rating,availability,first_seen_at,last_seen_at) '
            "VALUES(2,1,1,'https://books.toscrape.com/catalogue/unowned_2/index.html',"
            "'Unowned legacy book',1300,3,'In stock',?,?)",
            (now,now),
        )
        for job_id in jobs:
            connection.execute(
                "INSERT INTO crawl_job_books(job_id,book_id,action,observed_price_pence,observed_rating,observed_at) "
                "VALUES(?,1,'NEW',?,?,?)",
                (job_id,example_book['price_pence'],example_book['rating'],now),
            )
        for user_id in (1,2):
            connection.execute(
                'INSERT INTO bookmarks(user_id,book_id,created_at) VALUES(?,1,?)',
                (user_id,now),
            )
        connection.commit()
        migrations._apply_user_isolation_upgrade(connection)
        copies=connection.execute(
            'SELECT user_id,source_url FROM books WHERE source_url=? ORDER BY user_id',
            (example_book['source_url'],),
        ).fetchall()
        assert [(row['user_id'],row['source_url']) for row in copies]==[
            (1,example_book['source_url']),(2,example_book['source_url']),
        ]
        unowned=connection.execute(
            'SELECT id,user_id FROM books WHERE source_url=?',
            ('https://books.toscrape.com/catalogue/unowned_2/index.html',),
        ).fetchone()
        assert unowned is not None and unowned['user_id'] is None
        assert len({row[0] for row in connection.execute('SELECT id FROM books')})==3
        assert connection.execute('SELECT COUNT(*) FROM bookmarks').fetchone()[0]==2
        assert connection.execute('PRAGMA foreign_key_check').fetchall()==[]
    finally:
        connection.close()


def test_active_job_enforced_by_unique_index(isolated_db):
    j=db.create_job(1)
    with pytest.raises(sqlite3.IntegrityError):
        with db.connect() as con:
            con.execute("INSERT INTO crawl_jobs(source_id,max_pages,status,created_at) VALUES(1,1,'PENDING','2026-10-21T00:00:00Z')")
    db.finish_job(j['id'],'FAILED','sandbox test')
    assert db.create_job(1)['id']>j['id']


def test_legacy_v2_upgrade_preserves_records_and_writes_backup(tmp_path,monkeypatch):
    path=tmp_path/'existing.db'
    sql=(Path(__file__).parent/'fixtures'/'schema_v2.sql').read_text(encoding='utf8')
    with sqlite3.connect(path) as con:
        con.executescript(sql)
        con.execute("INSERT INTO crawl_jobs(max_pages,status,created_at,started_at,finished_at,items_saved,new_books) VALUES(1,'COMPLETED','2026-01-01T00:00:00Z','2026-01-01T00:00:01Z','2026-01-01T00:00:02Z',1,1)")
        con.execute("INSERT INTO books(source_url,title,price_pence,rating,category,availability,first_seen_at,last_seen_at) VALUES('https://books.toscrape.com/catalogue/a_1/index.html','Legacy',1300,3,'History','In stock','2026-01-01T00:00:00Z','2026-01-01T00:00:00Z')")
    monkeypatch.setenv('CRAWLINSIGHT_DB_PATH',str(path))
    db.init_db()
    with db.connect() as con:
        assert con.execute('SELECT COUNT(*) FROM books').fetchone()[0]==1
        assert con.execute('SELECT category FROM v_books_detail').fetchone()[0]=='History'
        assert con.execute('SELECT COUNT(*) FROM crawl_jobs').fetchone()[0]==1
        assert con.execute('PRAGMA foreign_key_check').fetchall()==[]
        assert db.search_books(q='Legacy')['total']==1
        assert con.execute('PRAGMA integrity_check').fetchone()[0]=='ok'
    backups=list(tmp_path.glob('existing.before-v3-*.sqlite3'))
    assert len(backups)==1
    with sqlite3.connect(backups[0]) as b:
        assert b.execute('SELECT COUNT(*) FROM books').fetchone()[0]==1
        assert b.execute("SELECT name FROM sqlite_master WHERE name='sources'").fetchone() is None
    db.init_db() # does not overwrite or create second backup
    assert len(list(tmp_path.glob('existing.before-v3-*.sqlite3')))==1


def test_demo_separated_from_real_data(isolated_db,tmp_path):
    target=tmp_path/'CrawlInsight_DEMO.sqlite3'
    seed_demo(target)
    with open_ro(target) as con:
        assert len(rows_of(con,'books',50))==12
        assert len(rows_of(con,'crawl_jobs',50))==2
        assert len(rows_of(con,'book_price_history',50))==1
        assert all('[DEMO]' in r['title'] for r in rows_of(con,'books',50))
        assert con.execute('PRAGMA integrity_check').fetchone()[0]=='ok'
    assert db.summary()['total_books']==0
    with pytest.raises(FileExistsError):seed_demo(target)
    with pytest.raises(ValueError):seed_demo(isolated_db)


def test_read_only_inspector_rejects_updates(isolated_db):
    with open_ro(isolated_db) as con:
        with pytest.raises(sqlite3.OperationalError):
            con.execute("DELETE FROM sources")
        with pytest.raises(ValueError):
            rows_of(con,'sqlite_master')


def test_safe_legacy_import_from_old_data_folder(tmp_path,monkeypatch):
    from database.tools.import_legacy import import_database
    source=tmp_path/'old.db'
    target=tmp_path/'private'/'new.db'
    sql=(Path(__file__).parent/'fixtures'/'schema_v2.sql').read_text(encoding='utf8')
    with sqlite3.connect(source) as con:
        con.executescript(sql)
        con.execute("INSERT INTO books(source_url,title,price_pence,rating,category,availability,first_seen_at,last_seen_at) VALUES('https://books.toscrape.com/catalogue/old_1/index.html','Old book',1234,3,'History','In stock','2026-01-01T00:00:00Z','2026-01-01T00:00:00Z')")
    result=import_database(source,target)
    assert result==target
    assert source.exists()
    assert target.exists()
    with sqlite3.connect(source) as con:
        assert con.execute('SELECT COUNT(*) FROM books').fetchone()[0]==1
        assert con.execute("SELECT name FROM sqlite_master WHERE name='sources'").fetchone() is None
    with sqlite3.connect(target) as con:
        assert con.execute('SELECT COUNT(*) FROM books').fetchone()[0]==1
        assert con.execute('SELECT category FROM v_books_detail').fetchone()[0]=='History'
        assert con.execute('PRAGMA foreign_key_check').fetchall()==[]
    with pytest.raises(FileExistsError):import_database(source,target)
