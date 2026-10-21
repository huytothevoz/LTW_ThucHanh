"""Book validation, normalized categories, item upsert, price audit and search."""
from __future__ import annotations
import re
from decimal import Decimal, InvalidOperation
from urllib.parse import urldefrag,urlsplit
from .connection import connect,now_utc

PRICE_PATTERN = re.compile(r'(?:0|[1-9]\d{0,3})(?:\.\d{1,2})?\Z')


class InvalidBookError(ValueError):
    """Crawler result failed the source-specific data contract."""


def validate_book(item: dict) -> dict:
    required = ('source_url','title','price_pence','rating','category','availability')
    if not isinstance(item, dict) or any(item.get(field) is None for field in required):
        raise InvalidBookError('Missing mandatory book field')
    url,_ = urldefrag(str(item['source_url']))
    parts=urlsplit(url)
    if parts.scheme!='https' or parts.hostname!='books.toscrape.com' or parts.port is not None or parts.username or parts.password or parts.query:
        raise InvalidBookError('Unapproved book URL')
    if not parts.path.startswith('/catalogue/') or not parts.path.endswith('/index.html'):
        raise InvalidBookError('Invalid detail URL path')
    if len(url)>2000:
        raise InvalidBookError('Book URL too long')
    if type(item['price_pence']) is not int or not 0 <= item['price_pence'] <= 999999:
        raise InvalidBookError('price_pence must be a non-negative integer <=999999')
    if type(item['rating']) is not int or item['rating'] not in range(1,6):
        raise InvalidBookError('rating must be 1–5')
    result={'source_url':url,'price_pence':item['price_pence'],'rating':item['rating']}
    for field in ('title','category','availability'):
        val=' '.join(str(item[field]).split())
        if not val:
            raise InvalidBookError(f'Empty {field}')
        result[field] = val[:500]
    for field in ('image_url','upc'):
        val=item.get(field)
        result[field] = str(val).strip()[:1000] if val else None
    if result['image_url']:
        p=urlsplit(result['image_url'])
        if p.scheme!='https' or p.hostname!='books.toscrape.com' or p.username or p.password or p.port:
            result['image_url']=None
    return result


def save_book_for_job(job_id: int, book: dict) -> str:
    """One transaction: category upsert + book upsert + audit rows + job counters.

    Per-job repeated items do not increment counters twice. Price change history
    is written only when the persisted price actually changes.
    """
    data=validate_book(book)
    when=now_utc()
    with connect() as con:
        con.execute('BEGIN IMMEDIATE')
        job=con.execute('SELECT status,source_id FROM crawl_jobs WHERE id=?',(job_id,)).fetchone()
        if job is None or job['status']!='RUNNING':
            raise RuntimeError('Cannot save a book for a non-running job')
        source_id=int(job['source_id'])
        con.execute('INSERT OR IGNORE INTO categories(source_id,name,first_seen_at) VALUES(?,?,?)', (source_id,data['category'],when))
        category=con.execute('SELECT id FROM categories WHERE source_id=? AND name=? COLLATE NOCASE', (source_id,data['category'])).fetchone()
        existing=con.execute('SELECT * FROM books WHERE source_url=?',(data['source_url'],)).fetchone()
        if existing and existing['source_id']!=source_id:
            raise InvalidBookError('Source collision in books table')
        if existing:
            prior_observation=con.execute('SELECT id FROM crawl_job_books WHERE job_id=? AND book_id=?',(job_id,existing['id'])).fetchone()
            if prior_observation:
                return 'existing'
            update_kind = 'UPDATED' if any((
                existing['title'] != data['title'],
                existing['price_pence'] != data['price_pence'],
                existing['rating'] != data['rating'],
                existing['category_id'] != category['id'],
                existing['availability'] != data['availability'],
                existing['image_url'] != data['image_url'],
                existing['upc'] != data['upc'],
            )) else 'UNCHANGED'
            if existing['price_pence']!=data['price_pence']:
                con.execute('INSERT INTO book_price_history(book_id,job_id,old_price_pence,new_price_pence,changed_at) VALUES(?,?,?,?,?)', (existing['id'],job_id,existing['price_pence'],data['price_pence'],when))
            con.execute('UPDATE books SET category_id=?,title=?,price_pence=?,rating=?,availability=?,image_url=?,upc=?,last_seen_at=?,last_crawl_job_id=? WHERE id=?', (category['id'],data['title'],data['price_pence'],data['rating'],data['availability'],data['image_url'],data['upc'],when,job_id,existing['id']))
            book_id=existing['id']
            counter='existing_books'
            outcome='existing'
        else:
            cur=con.execute('INSERT INTO books(source_id,category_id,source_url,title,price_pence,rating,availability,image_url,upc,first_seen_at,last_seen_at,last_crawl_job_id) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)', (source_id,category['id'],data['source_url'],data['title'],data['price_pence'],data['rating'],data['availability'],data['image_url'],data['upc'],when,when,job_id))
            book_id=cur.lastrowid
            update_kind='NEW'
            counter='new_books'
            outcome='new'
        con.execute('INSERT INTO crawl_job_books(job_id,book_id,action,observed_price_pence,observed_rating,observed_at) VALUES(?,?,?,?,?,?)',(job_id,book_id,update_kind,data['price_pence'],data['rating'],when))
        # The column name is selected by trusted code, never from user input.
        con.execute(f'UPDATE crawl_jobs SET items_saved=items_saved+1,{counter}={counter}+1 WHERE id=?',(job_id,))
    return outcome


def parse_price_filter(value: str | None, key: str) -> int | None:
    if value is None or value=='':
        return None
    if not PRICE_PATTERN.fullmatch(value):
        raise ValueError(f'{key} must be GBP 0–9999.99 with up to 2 decimals')
    try:
        result=int(Decimal(value)*100)
    except (InvalidOperation,OverflowError):
        raise ValueError(f'Invalid {key}') from None
    if not 0<=result<=999999:
        raise ValueError(f'{key} is out of range')
    return result


def search_books(q: str='',min_price: str|None=None,max_price: str|None=None,page: int=1)->dict:
    if len(q)>100:
        raise ValueError('q must be <=100 characters')
    if type(page) is not int or not 1<=page<=100000:
        raise ValueError('page must be between 1 and 100000')
    low=parse_price_filter(min_price,'min_price')
    high=parse_price_filter(max_price,'max_price')
    if low is not None and high is not None and low>high:
        raise ValueError('min_price must be <= max_price')
    conditions=[]
    params=[]
    if q.strip():
        escaped=q.strip().replace('\\','\\\\').replace('%','\\%').replace('_','\\_')
        conditions.append("b.title LIKE ? ESCAPE '\\' COLLATE NOCASE")
        params.append(f'%{escaped}%')
    if low is not None:
        conditions.append('b.price_pence>=?');params.append(low)
    if high is not None:
        conditions.append('b.price_pence<=?');params.append(high)
    where=' WHERE '+' AND '.join(conditions) if conditions else ''
    join=' FROM books b JOIN categories c ON c.id=b.category_id'
    with connect() as con:
        count=con.execute('SELECT COUNT(*)'+join+where,params).fetchone()[0]
        rows=con.execute('SELECT b.id,b.title,b.price_pence,b.rating,c.name AS category,b.availability,b.image_url,b.source_url'+join+where+' ORDER BY b.id DESC LIMIT 12 OFFSET ?', [*params,(page-1)*12]).fetchall()
    return {'items':[dict(r) for r in rows], 'page':page,'page_size':12,'total':count,'total_pages':(count+11)//12}
