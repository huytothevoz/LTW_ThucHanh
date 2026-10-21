"""Generate an OFFLINE read-only HTML report of schema and sample rows.

Usage: python -m database.tools.generate_report --db database/examples/CrawlInsight_DEMO.sqlite3
WARNING: output contains a copy of sampled data; don't publish report publicly.
"""
from __future__ import annotations
import argparse
import html
import sqlite3
from pathlib import Path
from .db_cli import DB_PATH,DEMO_PATH,open_ro

ROOT=Path(__file__).resolve().parents[2]

DESCRIPTIONS={
 'sources':'Nguồn website được cấp phép. Chỉ Books to Scrape đang được tích hợp.',
 'categories':'Danh mục sách duy nhất trong một nguồn, được tạo khi crawler tìm thấy.',
 'books':'Bản ghi sách mới nhất. Một URL chi tiết = một quyển sách duy nhất.',
 'crawl_jobs':'Mỗi lần nhấn Start tạo một job và ghi trạng thái, thời điểm, bộ đếm.',
 'crawl_pages':'Những trang catalogue thực sự đã xử lý trong mỗi job.',
 'crawl_job_books':'Liên kết sách với lượt crawl, phân loại NEW / UPDATED / UNCHANGED.',
 'book_price_history':'Chỉ ghi lại giá cũ và giá mới khi có thay đổi qua các lượt.',
 'crawl_events':'Nhật ký trạng thái, lỗi được làm sạch và sự kiện crawler.',
 'schema_migrations':'Lịch sử cập nhật cấu trúc database để không chạy lại nhầm.',
 'users':'Tài khoản cá nhân, scrypt password hash, session_version để thu hồi phiên cũ.',
 'user_preferences':'Ngôn ngữ vi/en, giao diện sáng/tối/hệ thống, kiểu hiển thị sách của từng user.',
 'bookmarks':'Sách yêu thích của riêng từng user, một sách không bị lưu trùng trong cùng tài khoản.',
 'saved_searches':'Bộ lọc tìm kiếm được mỗi tài khoản đặt tên và lưu.',
 'password_reset_tokens':'Mã đặt lại mật khẩu dạng HASH SHA-256, thời hạn 20 phút, một lần dùng.',
 'auth_attempts':'Dữ liệu giới hạn đăng nhập/khôi phục nhằm ngăn đoán mật khẩu hàng loạt.',
 'v_books_detail':'View JOIN sách + danh mục + nguồn, hiển thị giá GBP dễ đọc.',
 'v_category_summary':'View tổng số sách / giá trung bình / rating theo danh mục.',
 'v_job_overview':'View số sách mới / cập nhật / không đổi trong từng lượt.',
}


def esc(value):
    if value is None:return '<span class="empty">NULL</span>'
    text=str(value)
    if len(text)>210:text=text[:210]+'…'
    return html.escape(text,quote=True)


def generate(src:Path,output:Path,max_rows:int=15)->Path:
    if not 1<=max_rows<=50:raise ValueError('max_rows must be between 1 and 50')
    if output.exists() and output.resolve()==src.resolve():raise ValueError('Cannot overwrite database with HTML')
    with open_ro(src) as con:
        objects=[(r['name'],r['type']) for r in con.execute("SELECT name,type FROM sqlite_master WHERE type IN ('table','view') AND name NOT LIKE 'sqlite_%' ORDER BY type,name")]
        blocks=[]
        nav=[]
        total_objects=0
        for name,kind in objects:
            total_objects+=1
            ident='obj-'+name
            safe='"'+name+'"'
            count=con.execute('SELECT COUNT(*) FROM '+safe).fetchone()[0]
            columns=[dict(r) for r in con.execute('PRAGMA table_info('+safe+')')]
            fks=[dict(r) for r in con.execute('PRAGMA foreign_key_list('+safe+')')]
            rows=[dict(r) for r in con.execute('SELECT * FROM '+safe+' LIMIT ?', (max_rows,))]
            nav.append(f'<a href="#{ident}"><span>{html.escape(name)}</span><small>{count}</small></a>')
            coltags=''.join(f'<tr><td><code>{html.escape(c["name"])}</code></td><td>{esc(c["type"])}</td><td>{"Yes" if c["notnull"] else "No"}</td><td>{"Yes" if c["pk"] else "—"}</td></tr>' for c in columns)
            fklist=''.join(f'<li><code>{html.escape(k["from"])}</code> → <code>{html.escape(k["table"])}.{html.escape(k["to"])}</code></li>' for k in fks) or '<li>Không có khóa ngoại</li>'
            heads=''.join('<th>'+html.escape(c['name'])+'</th>' for c in columns)
            cells=''.join('<tr>'+''.join('<td>'+esc(row[c['name']])+'</td>' for c in columns)+'</tr>' for row in rows)
            if not cells:cells='<tr><td colspan="'+str(max(1,len(columns)))+'" class="zero">Chưa có bản ghi</td></tr>'
            blocks.append(f'''<section class="panel" id="{ident}">
              <header><div><div class="eyebrow">{kind.upper()} · {count} records</div><h2>{html.escape(name)}</h2><p>{html.escape(DESCRIPTIONS.get(name,''))}</p></div><a class="toplink" href="#top">↑ Lên đầu</a></header>
              <details><summary>Định nghĩa cột và khóa ngoại</summary>
              <div class="tablewrap"><table><thead><tr><th>Cột</th><th>Kiểu</th><th>NOT NULL</th><th>PK</th></tr></thead><tbody>{coltags}</tbody></table></div>
              <h3>Quan hệ tham chiếu</h3><ul>{fklist}</ul></details>
              <div class="tablewrap"><table><thead><tr>{heads}</tr></thead><tbody>{cells}</tbody></table></div>
              <p class="foot">Hiển thị tối đa {max_rows} bản ghi đầu tiên. Dữ liệu chỉ đọc, không sửa database.</p>
            </section>''')
    is_demo='DEMO' in src.name.upper()
    notice='DỮ LIỆU MINH HỌA — KHÔNG PHẢI KẾT QUẢ WEB CRAWLING' if is_demo else 'BÁO CÁO DATABASE — dữ liệu được chụp tại thời điểm tạo file'
    css='''
:root{font-family:Inter,Segoe UI,system-ui,sans-serif;color:#e9eef9;background:#09101f;color-scheme:dark}*{box-sizing:border-box}body{margin:0}a{color:#8ab4ff;text-decoration:none}.layout{display:grid;grid-template-columns:265px minmax(0,1fr);min-height:100vh}aside{border-right:1px solid #25354e;background:#0c1729;padding:28px 16px;position:sticky;top:0;height:100vh;overflow:auto}aside h1{font-size:18px;margin:8px 10px 24px}aside nav a{display:flex;align-items:center;justify-content:space-between;color:#b4c5de;padding:11px;border-radius:9px;font-size:13px;gap:8px}aside nav a:hover{background:#1c2e47;color:white}aside small{background:#1e3450;border-radius:99px;padding:2px 8px}main{padding:30px min(4vw,48px);min-width:0;max-width:1600px}.hero{background:linear-gradient(120deg,#123966,#101e36 65%);border:1px solid #284f7d;padding:30px;border-radius:20px;margin-bottom:25px}.hero h1{font-size:29px;margin:10px 0}.hero p{color:#bcd1ec;line-height:1.7}.label{font-size:11px;letter-spacing:2px;color:#76c8ee;font-weight:750}.warning{background:#52411c;border:1px solid #a9832c;padding:12px 16px;border-radius:11px;color:#ffe8b0;margin-top:16px;font-size:13px}.statbar{display:flex;gap:12px;flex-wrap:wrap;margin-top:20px}.stat{background:#07192e;border:1px solid #35547c;padding:14px 19px;border-radius:12px}.stat b{font-size:22px;display:block}.stat span{font-size:12px;color:#adc0db}.panel{background:#121f31;border:1px solid #263b57;border-radius:17px;padding:23px;margin:24px 0;scroll-margin-top:20px}.panel header{display:flex;justify-content:space-between;gap:12px}.panel h2{margin:8px 0 4px;font-size:21px}.panel p{color:#9fb0c6;font-size:13px;line-height:1.6}.eyebrow{font-weight:750;color:#68d9cb;font-size:10px;letter-spacing:1.7px}.toplink{font-size:12px;white-space:nowrap}details{background:#0d192b;border:1px solid #253e5a;padding:10px 13px;margin:15px 0;border-radius:9px}summary{cursor:pointer;font-weight:650;font-size:13px}h3{font-size:13px}li{font-size:12px;line-height:1.8;color:#c6d5e8}.tablewrap{overflow:auto;max-width:100%;border-radius:10px;border:1px solid #283e57;margin:14px 0}table{border-collapse:collapse;font-size:12px;width:100%}th,td{padding:12px 11px;border-bottom:1px solid #2b3d55;white-space:nowrap;text-align:left;max-width:260px;overflow:hidden;text-overflow:ellipsis}th{color:#a8c2df;background:#152842;font-weight:750}td{color:#dce7f7}tr:nth-child(2n){background:#132238}code{font-family:Consolas,monospace;color:#81c5fa}.empty{color:#6b809b}.foot{font-size:11px!important}.zero{text-align:center;color:#8eabc8} .brand{font-weight:800;letter-spacing:.2px;color:white} @media(max-width:850px){.layout{display:block}aside{position:static;height:auto;border-right:none;border-bottom:1px solid #25354e}aside nav{display:flex;overflow:auto}aside nav a{flex-shrink:0}main{padding:16px}.hero{padding:20px}.panel{padding:14px}}
'''
    output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(f'''<!doctype html><html lang="vi"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>LTW-TH · Database Explorer</title><style>{css}</style></head><body><div class="layout"><aside><div class="brand">◈ CrawlInsight</div><h1>Database Explorer</h1><nav>{''.join(nav)}</nav></aside><main><div class="hero" id="top"><div class="label">DATABASE DOCUMENTATION · V4</div><h1>Khám phá cơ sở dữ liệu LTW-TH</h1><p>Từng bảng có mục đích, định nghĩa trường, khóa ngoại và dữ liệu mẫu có thể xem được. Đây là HTML snapshot tạo từ SQLite: không sửa dữ liệu và không yêu cầu cài thư viện frontend.</p><div class="warning">{html.escape(notice)}<br>Nguồn file: <code>{html.escape(src.name)}</code>. Không đăng công khai bản báo cáo chứa dữ liệu thực.</div><div class="statbar"><div class="stat"><b>{total_objects}</b><span>Bảng và view</span></div><div class="stat"><b>{sum(1 for _,t in objects if t=='table')}</b><span>Bảng dữ liệu</span></div><div class="stat"><b>{sum(1 for _,t in objects if t=='view')}</b><span>View truy vấn</span></div></div></div>{''.join(blocks)}</main></div></body></html>''',encoding='utf-8')
    return output


def main():
    parser=argparse.ArgumentParser(description='Create a readable offline database schema/data report')
    parser.add_argument('--db',type=Path,default=DEMO_PATH)
    parser.add_argument('--output',type=Path,default=ROOT/'database'/'examples'/'Database_Explorer_DEMO.html')
    parser.add_argument('--limit',type=int,default=15)
    args=parser.parse_args()
    print('Generated:',generate(args.db.resolve(),args.output.resolve(),args.limit))

if __name__=='__main__':main()
