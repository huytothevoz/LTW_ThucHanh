"""CrawlInsight DB toolbox. Usage: python -m database.tools.db_cli --help

Every inspection/export opens the target SQLite database READ-ONLY and never
creates a new DB implicitly. `init`, `backup` and `demo` are explicit commands.
"""
from __future__ import annotations
import argparse
import csv
import json
import os
import sqlite3
from pathlib import Path
from src import db

PROJECT_ROOT=Path(__file__).resolve().parents[2]
DEMO_PATH=PROJECT_ROOT/'database'/'examples'/'CrawlInsight_DEMO.sqlite3'
DB_PATH=db.DEFAULT_DB


def open_ro(path:Path)->sqlite3.Connection:
    if not path.is_file():
        raise FileNotFoundError(f'Database not found: {path}. Run init first.')
    con=sqlite3.connect(path.as_uri()+'?mode=ro',uri=True,timeout=5)
    con.row_factory=sqlite3.Row
    con.execute('PRAGMA query_only=ON')
    return con


def object_name(con:sqlite3.Connection,name:str)->str:
    if not name or name.startswith('sqlite_'):
        raise ValueError('System tables and unknown names are not available')
    row=con.execute("SELECT name FROM sqlite_master WHERE name=? AND type IN ('table','view')",(name,)).fetchone()
    if row is None:
        raise ValueError(f'Unknown table/view: {name}')
    return '"'+row[0].replace('"','""')+'"'


def pretty(rows:list[dict], limit:int=40):
    if not rows:
        print('(empty)');return
    cols=list(rows[0])
    widths={c:min(48,max(len(c),*(len(str(r.get(c))) for r in rows))) for c in cols}
    print(' | '.join(c[:widths[c]].ljust(widths[c]) for c in cols))
    print('-+-'.join('-'*widths[c] for c in cols))
    for row in rows[:limit]:
        print(' | '.join(str(row.get(c,''))[:widths[c]].ljust(widths[c]) for c in cols))


def rows_of(con, name:str, limit:int=12):
    safe=object_name(con,name)
    return [dict(r) for r in con.execute(f'SELECT * FROM {safe} LIMIT ?', (limit,))]


def seed_demo(path:Path):
    """Create a separate clearly labeled example file; never touches live DB."""
    path=path.resolve()
    if path==DB_PATH.resolve() or path==db.database_path().resolve():
        raise ValueError('Refusing to insert demo records into the live DB')
    if path.exists():
        raise FileExistsError(f'Demo target already exists; not overwriting: {path}')
    path.parent.mkdir(parents=True,exist_ok=True)
    prev=os.environ.get('CRAWLINSIGHT_DB_PATH')
    os.environ['CRAWLINSIGHT_DB_PATH']=str(path)
    try:
        db.init_db()
        with db.connect() as con:
            con.execute("UPDATE sources SET name='Books to Scrape — DEMO DATA (never crawled)' WHERE id=1")
        titles=[
            ('[DEMO] A Gentle Introduction to Python','Programming',1750,4),
            ('[DEMO] Understanding the Web','Technology',2599,5),
            ('[DEMO] Learning Search Algorithms','Science',1249,3),
            ('[DEMO] The Art of Databases','Technology',3140,5),
            ('[DEMO] A Quiet Morning','Fiction',799,2),
            ('[DEMO] The Ocean Atlas','Travel',3555,4),
            ('[DEMO] Everyday Statistics','Science',2050,3),
            ('[DEMO] Coding Together','Programming',2899,5),
            ('[DEMO] A Winter Letter','Fiction',1595,4),
            ('[DEMO] Cities and Rivers','Travel',4320,3),
            ('[DEMO] Data Ethics 101','Technology',1930,5),
            ('[DEMO] The Small Library','Fiction',1199,4),
        ]
        first=db.create_job(1); db.mark_job_running(first['id'])
        db.record_catalogue_page(first['id'],'https://books.toscrape.com/',1,len(titles))
        for i,(title,category,pence,rating) in enumerate(titles,1):
            db.save_book_for_job(first['id'],{'source_url':f'https://books.toscrape.com/catalogue/demo_sample_{i:03d}/index.html',
                'title':title,'category':category,'price_pence':pence,'rating':rating,
                'availability':'In stock','image_url':None,'upc':f'DEMO-{i:03d}'})
        db.finish_job(first['id'],'COMPLETED')
        second=db.create_job(1);db.mark_job_running(second['id'])
        db.record_catalogue_page(second['id'],'https://books.toscrape.com/',1,3)
        for i in (1,2,3):
            title,category,pence,rating=titles[i-1]
            db.save_book_for_job(second['id'],{'source_url':f'https://books.toscrape.com/catalogue/demo_sample_{i:03d}/index.html',
                'title':title,'category':category,'price_pence':(pence+200 if i==2 else pence),
                'rating':rating,'availability':'In stock','image_url':None,'upc':f'DEMO-{i:03d}'})
        db.finish_job(second['id'],'COMPLETED')
        with db.connect() as con:
            result=con.execute('PRAGMA integrity_check').fetchone()[0]
            if result!='ok':raise RuntimeError(result)
            con.execute('PRAGMA wal_checkpoint(TRUNCATE)')
    except BaseException:
        # Preserve broken demo for investigation; never silently clean the data.
        raise
    finally:
        if prev is None:os.environ.pop('CRAWLINSIGHT_DB_PATH',None)
        else:os.environ['CRAWLINSIGHT_DB_PATH']=prev
    return path


def main(argv=None):
    p=argparse.ArgumentParser(description='Inspect, initialize, verify, backup and export CrawlInsight SQLite')
    p.add_argument('--db',type=Path,default=DB_PATH,help='SQLite file; defaults to data/crawlinsight.db')
    sub=p.add_subparsers(dest='command',required=True)
    sub.add_parser('init',help='Create/migrate v3 (backs up legacy v2 automatically)')
    sub.add_parser('tables',help='List tables/views and row counts')
    d=sub.add_parser('describe',help='Columns, types, PK and foreign keys');d.add_argument('table')
    r=sub.add_parser('rows',help='Read only first N rows of a table/view');r.add_argument('table');r.add_argument('--limit',type=int,default=12)
    sub.add_parser('check',help='integrity_check, foreign_key_check and applied migrations')
    b=sub.add_parser('backup',help='Consistent non-destructive SQLite backup');b.add_argument('--output',type=Path,required=True)
    e=sub.add_parser('export',help='Export one table/view as CSV/JSON');e.add_argument('table');e.add_argument('--format',choices=('csv','json'),default='csv');e.add_argument('--output',type=Path,required=True)
    dm=sub.add_parser('demo',help='Create SEPARATE demo database (no live books)');dm.add_argument('--output',type=Path,default=DEMO_PATH)
    args=p.parse_args(argv)
    if args.command=='demo':print('Created synthetic demo database:',seed_demo(args.output));return
    path=args.db.expanduser().resolve()
    if args.command=='init':
        prev=os.environ.get('CRAWLINSIGHT_DB_PATH')
        os.environ['CRAWLINSIGHT_DB_PATH']=str(path)
        try:db.init_db()
        finally:
            if prev is None:os.environ.pop('CRAWLINSIGHT_DB_PATH',None)
            else:os.environ['CRAWLINSIGHT_DB_PATH']=prev
        print('Database initialized/migrated:',path);return
    with open_ro(path) as con:
        if args.command=='tables':
            for r in con.execute("SELECT name,type FROM sqlite_master WHERE type IN ('table','view') AND name NOT LIKE 'sqlite_%' ORDER BY type,name"):
                safe=object_name(con,r['name'])
                print(f"{r['type']:5s} {r['name']:23s} {con.execute('SELECT COUNT(*) FROM '+safe).fetchone()[0]:>6} rows")
        elif args.command=='describe':
            safe=object_name(con,args.table)
            pretty([dict(r) for r in con.execute(f'PRAGMA table_info({safe})')])
            print('\nForeign keys:')
            pretty([dict(r) for r in con.execute(f'PRAGMA foreign_key_list({safe})')])
        elif args.command=='rows':
            if not 1<=args.limit<=500:raise ValueError('--limit must be 1..500')
            pretty(rows_of(con,args.table,args.limit))
        elif args.command=='check':
            print('integrity_check:',con.execute('PRAGMA integrity_check').fetchone()[0])
            problems=list(con.execute('PRAGMA foreign_key_check'))
            print('foreign_key_check:',len(problems),'issues')
            if problems:pretty([dict(r) for r in problems])
            print('schema migrations:');pretty(rows_of(con,'schema_migrations'))
            if problems:raise SystemExit(2)
        elif args.command=='export':
            safe=object_name(con,args.table)
            output=args.output.expanduser().resolve()
            if output.exists():raise FileExistsError(f'Export already exists: {output}')
            output.parent.mkdir(parents=True,exist_ok=True)
            headers=[r['name'] for r in con.execute(f'PRAGMA table_info({safe})')]
            if args.format=='json':
                data=[dict(r) for r in con.execute('SELECT * FROM '+safe)]
                output.write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')
            else:
                # utf-8-sig opens Vietnamese correctly in many Excel versions.
                with output.open('w',encoding='utf-8-sig',newline='') as f:
                    w=csv.writer(f);w.writerow(headers)
                    for row in con.execute('SELECT * FROM '+safe):w.writerow(tuple(row))
            print('Exported:',output)
        elif args.command=='backup':
            output=args.output.expanduser().resolve()
            if output.exists():raise FileExistsError(f'Backup already exists: {output}')
            if output==path:raise ValueError('Backup path must differ from the source')
            output.parent.mkdir(parents=True,exist_ok=True)
            with sqlite3.connect(str(path)) as source:
                with sqlite3.connect(str(output)) as target:
                    source.backup(target)
            print('Backed up:',output)

if __name__=='__main__':
    try:main()
    except (ValueError,FileNotFoundError,FileExistsError,sqlite3.Error) as exc:
        raise SystemExit(f'ERROR: {exc}')
