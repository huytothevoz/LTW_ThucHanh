# CRAWLINSIGHT — IMPLEMENTATION STATUS & HANDOFF (CONSOLIDATED)

**Dự án:** `LTW-TH` · **Học phần:** 503073 · **Đề tài:** 07 — Web Crawling  
**Phiên bản:** Implementation 4.2 — Consolidated · **Snapshot:** 21/10/2026  
**Pha RUP:** `03_construction` · **Trạng thái:** Có source V4, **chưa nghiệm thu end-to-end trên máy nhóm**.  
**Liên kết:** SRS `../02_elaboration/SRS_CrawlInsight_Consolidated.md`; API `../02_elaboration/API_CrawlInsight_Consolidated.md`.

> **Nguồn hợp nhất:** `docs/IMPLEMENTATION_STATUS.md` (v1/v3), `docs/IMPLEMENTATION_STATUS_V4.md`, source `LTW-TH_Source_V4_FullPlatform.zip`, kiểm tra source/tests ngày 21/10/2026. Tài liệu này **thay thế hai bản trạng thái cũ**; thông tin về website 2 màn hình, không có tài khoản và database 2 bảng là lịch sử, không phải trạng thái hiện tại.

## 1. Quy tắc ghi trạng thái, không tô hồng tiến độ

| Trạng thái | Ý nghĩa | Minh chứng cần có |
|---|---|---|
| `CODED` | Module/route/file đã tồn tại và được kết nối trong source. | File/commit/route cụ thể. |
| `UNIT_PASS` | Test độc lập/fixture hoặc SQL chạy đạt trong môi trường kiểm tra. | Test name + kết quả. |
| `HTTP_PENDING` | Chưa chạy đủ Flask HTTP integration do thiếu dependency. | Chạy pytest trên máy nhóm. |
| `LIVE_PENDING` | Chưa chạy crawler thật/SMTP/browser trên Windows. | Log, screenshot, trace, DB records. |
| `QA_PASS` | Có test thực tế đạt theo TC trong SRS và reviewer ký. | Evidence + PR/commit + ngày. |
| `BLOCKED` | Không triển khai tiếp được, có lỗi/phụ thuộc cụ thể. | Issue mô tả cách tái hiện. |
| `BACKLOG` | Chưa triển khai trong source V4. | Chỉ làm khi scope được duyệt. |

**Nguyên tắc:** `CODED` ≠ `UNIT_PASS` ≠ `QA_PASS`. Không gán % hoàn thành chỉ từ số file/màn hình. 50 test PASS phản ánh phần kiểm thử thực thi được **ở lớp offline**, 4 SKIP không được ghi là PASS.

## 2. Snapshot code và kết quả kiểm tra

| Thành phần | Có code | Đã kiểm chứng trong môi trường hiện tại | Chưa xác minh/điều kiện Done |
|---|---|---|---|
| Landing + navigation | Có | Render template VI/EN, kiểm cú pháp HTML/Jinja qua test | Chrome/Edge, mobile, CTA thật |
| Register/login/logout/session | Có | SQLite auth/scrypt/uniqueness/session version test | HTTP integration, CSRF thật, cookie đa trình duyệt |
| Forgot/reset/password change | Có | Token hash/TTL/one-time, đổi mật khẩu unit | SMTP thật hoặc local test option, email delivery failure |
| Profile/preferences/i18n/theme | Có | Database preference, template VI/EN | Tương tác giao diện, refresh, dark/system, keyboard |
| Dashboard/books/search/filter | Có | SQL filter, pence, empty DB, template fixture | API/JS/live catalog + browser |
| Bookmark/saved search | Có | SQLite cross-user isolation, FK | HTTP + UI save/un-save, trình duyệt A/B |
| History/analytics/sources/CSV | Có | SQL/views/DB tests; code route tồn tại | Kết quả live, số liệu thống nhất, Excel CSV formula safety |
| Scrapy crawler/worker | Có | URL policy/parser helpers/settings test | Scrapy fixture test thiếu dependency, crawl live 1–3 trang |
| SQLite V4 migrations | Có | Tạo V4, FK, integrity, upgrade giữ data từ V3 trong test | Backup trên máy nhóm; restore trên bản sao DB thật |
| Windows setup/local security | Có | Script nguồn, `.htaccess` và cấu hình local hiện diện | Máy Windows sạch/XAMPP Apache URL/access policy |

**Kiểm thử đã chạy lại:** từ bản source V4 ở môi trường làm việc, `python -m pytest -q` cho **50 passed, 4 skipped** vào ngày 21/10/2026. Những kiểm thử skip phụ thuộc Flask/Scrapy; **chưa có** bằng chứng E2E/SMTP/live crawl/browser được xác minh trong môi trường này. Không thay thế kết quả trên máy thực của nhóm bằng kết quả này.

### 2.1. Các module code đang làm nhiệm vụ gì

| Đường dẫn source | Chức năng hiện có | Ranh giới chỉnh sửa |
|---|---|---|
| `app.py` | Flask app/config, bảo mật chung, landing, `/api/health`, tạo/đọc job, spawn crawler | API & điều phối |
| `src/web/auth.py`, `security.py`, `mail.py` | Routes login/register/forgot/reset, CSRF, SMTP | Xác thực và bảo vệ HTTP |
| `src/web/workspace.py` | Workspace routes, books, bookmarks, saved search, history, analytics, sources, CSV | API nghiệp vụ và views |
| `src/database/accounts.py` | User, scrypt, preferences, reset token, bookmarks, saved-searches | Dữ liệu sở hữu tài khoản |
| `src/database/books.py` | Validate item, chuẩn hóa, upsert, price history, tìm kiếm | Dữ liệu nguồn dùng chung |
| `src/database/jobs.py` | Job states, counters, crawl events, page evidence | Trạng thái crawler |
| `src/database/migrations.py`, `connection.py` | Kết nối, migration, backup/upgrade, DB path | Toàn vẹn và vận hành DB |
| `crawler/spiders/books_spider.py`, `parser.py`, `pipelines.py`, `settings.py`, `run_job.py` | Crawl allowlist, parse HTML, pipeline, worker process | Thu thập nguồn sandbox |
| `templates/`, `static/css/`, `static/js/` | UI landing, auth, 8 trang workspace, responsive, VI/EN/theme | Frontend; tránh đổi API field tự ý |
| `database/migrations/001..004` | Schema nguồn/V3 và thêm identity V4 | Migration; không sửa lịch sử đã apply |
| `tests/` | Unit/fixture/Flask API tests | Cập nhật khi sửa hợp đồng |

## 3. Ma trận 50 FR hiện hành — code status & acceptance gate

Bảng này lấy nguyên **50 mã FR của SRS 4.2**, tránh gán lại mã FR-01…FR-21 của bản 2.0 cũ. `CODED` nghĩa là có phần triển khai, **không có nghĩa QC xong**. Kiểm thử chi tiết tuân theo 37 mã TC của SRS/Excel.

| FR | Yêu cầu hiện hành | Source chính | Trạng thái hiện có | Việc cần xác nhận để Done |
|---|---|---|---|---|
| FR-PUB-01 | Landing page giới thiệu CrawlInsight | `templates/index.html`, `app.py` | `CODED` | Chưa test trình duyệt; QA/E2E chưa ký |
| FR-PUB-02 | Điều hướng công khai sang tài khoản | `templates/index.html`, `app.py` | `CODED` | Chưa E2E; QA/E2E chưa ký |
| FR-PUB-03 | Giao diện landing tiếng Việt/Anh | `templates/index.html`, `app.py` | `CODED` | Render template offline; QA/E2E chưa ký |
| FR-PUB-04 | Empty state và nội dung trung thực | `templates/index.html`, `app.py` | `CODED` | Chưa E2E; QA/E2E chưa ký |
| FR-AUT-01 | Đăng ký người dùng | `src/web/auth.py`, `src/database/accounts.py` | `CODED` + một phần `UNIT_PASS` | Unit DB đạt; HTTP cần QA; QA/E2E chưa ký |
| FR-AUT-02 | Đăng nhập bằng email/mật khẩu | `src/web/auth.py`, `src/database/accounts.py` | `CODED` + một phần `UNIT_PASS` | Unit DB đạt; HTTP cần QA; QA/E2E chưa ký |
| FR-AUT-03 | Đăng xuất an toàn | `src/web/auth.py`, `src/database/accounts.py` | `CODED` | HTTP cần QA; QA/E2E chưa ký |
| FR-AUT-04 | Quên mật khẩu bằng token | `src/web/auth.py`, `src/database/accounts.py` | `CODED` + một phần `UNIT_PASS` | Unit token đạt; SMTP chưa xác minh; QA/E2E chưa ký |
| FR-AUT-05 | Gửi email khôi phục qua SMTP | `src/web/auth.py`, `src/database/accounts.py` | `CODED` | Chưa test email thật; QA/E2E chưa ký |
| FR-AUT-06 | Đổi mật khẩu sau đăng nhập | `src/web/auth.py`, `src/database/accounts.py` | `CODED` + một phần `UNIT_PASS` | Unit DB đạt; HTTP cần QA; QA/E2E chưa ký |
| FR-AUT-07 | Cập nhật họ tên | `src/web/auth.py`, `src/database/accounts.py` | `CODED` + một phần `UNIT_PASS` | Unit DB đạt; UI cần QA; QA/E2E chưa ký |
| FR-AUT-08 | Chống brute-force theo giới hạn | `src/web/auth.py`, `src/database/accounts.py` | `CODED` + một phần `UNIT_PASS` | Unit DB đạt; HTTP cần QA; QA/E2E chưa ký |
| FR-AUT-09 | Bảo vệ route và API đăng nhập | `src/web/auth.py`, `src/database/accounts.py` | `CODED` + một phần `UNIT_PASS` | Một phần unit; cần E2E; QA/E2E chưa ký |
| FR-AUT-10 | Kiểm soát phiên sau reset password | `src/web/auth.py`, `src/database/accounts.py` | `CODED` + một phần `UNIT_PASS` | Unit DB đạt; multi-session cần QA; QA/E2E chưa ký |
| FR-USR-01 | Ngôn ngữ VI/EN | `src/database/accounts.py`, `static/js/common.js` | `CODED` + một phần `UNIT_PASS` | Template offline; browser chưa QA; QA/E2E chưa ký |
| FR-USR-02 | Theme light/dark/system | `src/database/accounts.py`, `static/js/common.js` | `CODED` | CSS/Jinja kiểm tra; browser chưa QA; QA/E2E chưa ký |
| FR-USR-03 | Cài đặt cách hiển thị sách | `src/database/accounts.py`, `static/js/common.js` | `CODED` + một phần `UNIT_PASS` | Unit DB đạt; browser chưa QA; QA/E2E chưa ký |
| FR-USR-04 | Lưu và khôi phục preferences | `src/database/accounts.py`, `static/js/common.js` | `CODED` + một phần `UNIT_PASS` | Unit DB đạt; HTTP chưa QA; QA/E2E chưa ký |
| FR-USR-05 | Cách ly dữ liệu cá nhân nhiều tài khoản | `src/database/accounts.py`, `static/js/common.js` | `CODED` + một phần `UNIT_PASS` | Unit DB đạt; HTTP chưa QA; QA/E2E chưa ký |
| FR-CRW-01 | Khởi tạo crawl job có chủ sở hữu | `crawler/`, `src/database/jobs.py`, `app.py` | `CODED` + một phần `UNIT_PASS` | DB unit đạt; live chưa QA; QA/E2E chưa ký |
| FR-CRW-02 | Giới hạn 1–3 trang danh sách | `crawler/`, `src/database/jobs.py`, `app.py` | `CODED` + một phần `UNIT_PASS` | Unit đạt; live chưa QA; QA/E2E chưa ký |
| FR-CRW-03 | Một job hoạt động toàn hệ thống | `crawler/`, `src/database/jobs.py`, `app.py` | `CODED` + một phần `UNIT_PASS` | SQLite index/unit đạt; QA/E2E chưa ký |
| FR-CRW-04 | Crawler chỉ truy cập nguồn được phép | `crawler/`, `src/database/jobs.py`, `app.py` | `CODED` + một phần `UNIT_PASS` | Parser/policy unit; live chưa QA; QA/E2E chưa ký |
| FR-CRW-05 | Duyệt catalogue và next-page | `crawler/`, `src/database/jobs.py`, `app.py` | `CODED` | Spider test bị skip; live chưa QA; QA/E2E chưa ký |
| FR-CRW-06 | Truy xuất từng trang chi tiết sách | `crawler/`, `src/database/jobs.py`, `app.py` | `CODED` + một phần `UNIT_PASS` | Parser fixture đạt; live chưa QA; QA/E2E chưa ký |
| FR-CRW-07 | Tuân thủ robots và giảm tải nguồn | `crawler/`, `src/database/jobs.py`, `app.py` | `CODED` + một phần `UNIT_PASS` | Settings unit; live cần QA; QA/E2E chưa ký |
| FR-CRW-08 | Chống trùng và upsert bản ghi | `crawler/`, `src/database/jobs.py`, `app.py` | `CODED` + một phần `UNIT_PASS` | DB unit đạt; live chưa QA; QA/E2E chưa ký |
| FR-CRW-09 | Nhật ký job và số liệu tiến độ | `crawler/`, `src/database/jobs.py`, `app.py` | `CODED` + một phần `UNIT_PASS` | DB unit đạt; UI cần QA; QA/E2E chưa ký |
| FR-CRW-10 | Theo dõi job với polling | `crawler/`, `src/database/jobs.py`, `app.py` | `CODED` | HTTP/browser chưa QA; QA/E2E chưa ký |
| FR-CRW-11 | Xử lý hỏng request / lỗi parse | `crawler/`, `src/database/jobs.py`, `app.py` | `CODED` + một phần `UNIT_PASS` | Một phần unit; live lỗi chưa QA; QA/E2E chưa ký |
| FR-CRW-12 | Khôi phục job bị treo | `crawler/`, `src/database/jobs.py`, `app.py` | `CODED` | Chưa chạy tình huống kill process; QA/E2E chưa ký |
| FR-BOO-01 | Danh sách sách thật, có phân trang | `src/web/workspace.py`, `src/database/books.py` | `CODED` + một phần `UNIT_PASS` | DB unit đạt; browser chưa QA; QA/E2E chưa ký |
| FR-BOO-02 | Tìm kiếm sách theo tên | `src/web/workspace.py`, `src/database/books.py` | `CODED` + một phần `UNIT_PASS` | DB unit đạt; HTTP cần QA; QA/E2E chưa ký |
| FR-BOO-03 | Lọc khoảng giá GBP | `src/web/workspace.py`, `src/database/books.py` | `CODED` + một phần `UNIT_PASS` | DB unit đạt; UI cần QA; QA/E2E chưa ký |
| FR-BOO-04 | Xem chi tiết và lịch sử giá | `src/web/workspace.py`, `src/database/books.py` | `CODED` + một phần `UNIT_PASS` | DB unit; browser chưa QA; QA/E2E chưa ký |
| FR-BOO-05 | Lưu / bỏ lưu sách theo user | `src/web/workspace.py`, `src/database/books.py` | `CODED` + một phần `UNIT_PASS` | Unit cách ly đạt; UI chưa QA; QA/E2E chưa ký |
| FR-BOO-06 | Trang Sách đã lưu | `src/web/workspace.py`, `src/database/books.py` | `CODED` + một phần `UNIT_PASS` | Template; browser chưa QA; QA/E2E chưa ký |
| FR-BOO-07 | Lưu bộ lọc tìm kiếm cá nhân | `src/web/workspace.py`, `src/database/books.py` | `CODED` + một phần `UNIT_PASS` | Unit DB đạt; UI chưa QA; QA/E2E chưa ký |
| FR-BOO-08 | Xuất CSV Unicode | `src/web/workspace.py`, `src/database/books.py` | `CODED` | HTTP test bị skip; QA/E2E chưa ký |
| FR-WSP-01 | Tổng quan KPI/biểu đồ sao | `src/web/workspace.py`, `templates/` | `CODED` + một phần `UNIT_PASS` | DB unit; browser chưa QA; QA/E2E chưa ký |
| FR-WSP-02 | Lịch sử lượt crawl từng tài khoản | `src/web/workspace.py`, `templates/` | `CODED` | API cần E2E; QA/E2E chưa ký |
| FR-WSP-03 | Phân tích rating/category/price | `src/web/workspace.py`, `templates/` | `CODED` + một phần `UNIT_PASS` | SQL unit; browser chưa QA; QA/E2E chưa ký |
| FR-WSP-04 | Danh mục nguồn dữ liệu | `src/web/workspace.py`, `templates/` | `CODED` + một phần `UNIT_PASS` | DB unit; browser chưa QA; QA/E2E chưa ký |
| FR-WSP-05 | Trang Hướng dẫn sử dụng | `src/web/workspace.py`, `templates/` | `CODED` + một phần `UNIT_PASS` | Template; nội dung cần review; QA/E2E chưa ký |
| FR-WSP-06 | Responsive/navigational UX | `src/web/workspace.py`, `templates/` | `CODED` | Chưa visual QA thật; QA/E2E chưa ký |
| FR-PLT-01 | CSRF trên mutation API | `app.py`, `src/web/security.py`, `database/migrations/` | `CODED` + một phần `UNIT_PASS` | HTTP unit bị skip; QA/E2E chưa ký |
| FR-PLT-02 | Security headers và cookies | `app.py`, `src/web/security.py`, `database/migrations/` | `CODED` | Chưa HTTP browser QA; QA/E2E chưa ký |
| FR-PLT-03 | Migration V3→V4 và backup | `app.py`, `src/web/security.py`, `database/migrations/` | `CODED` + một phần `UNIT_PASS` | Unit migration đạt; QA/E2E chưa ký |
| FR-PLT-04 | Setup an toàn và môi trường chạy | `app.py`, `src/web/security.py`, `database/migrations/` | `CODED` | Chưa test Windows sạch; QA/E2E chưa ký |
| FR-PLT-05 | Thông báo lỗi và trạng thái hệ thống | `app.py`, `src/web/security.py`, `database/migrations/` | `CODED` | Chưa E2E; QA/E2E chưa ký |

## 4. Những điểm dễ lỗi/mâu thuẫn cần xử lý ưu tiên

| Ưu tiên | Vấn đề từ code/baseline | Hướng kiểm tra/sửa | Người phụ trách đề xuất |
|---|---|---|---|
| P0 | 4 bài test phụ thuộc Flask/Scrapy chưa chạy trong môi trường tạo source. | Cài `requirements.txt`, chạy toàn bộ pytest; fix lỗi thật, không dùng skip. | Duy + Quý |
| P0 | Crawler live chưa có chứng cứ end-to-end (1–3 trang, detail, robots, counters). | Chạy 1 và 2 trang, đối chiếu `crawl_pages`, `books`, logs, jobs; chụp minh chứng. | Quý |
| P0 | CSRF/token phiên sau login/logout và session reset chưa được xác minh thực tế. | Test browser cookie jar, 403 thiếu token, reset token 1 lần, 2 sessions. | Duy |
| P0 | `POST /api/jobs`: bản ghi job được tạo rồi `user_id` được gán trong một transaction riêng. | Rà trường hợp lỗi/race giữa hai thao tác; cân nhắc create_job(owner) nguyên tử, kèm regression test. | Duy |
| P0 | CSV xuất các trường từ dữ liệu thu thập trực tiếp qua csv.writer. | Test và phòng CSV formula injection (`=`, `+`, `-`, `@`) trước khi xem là nghiệm thu TC-28. | Duy |
| P0 | Runtime DB, secret và source nằm trong thư mục XAMPP `htdocs` nếu copy sai. | Chỉ chạy Flask 127.0.0.1; kiểm Apache 403 và đường DB nằm ngoài web root. | Duy |
| P1 | UI chưa được kiểm trên mobile/browser real; có rủi ro font/i18n/layout. | Test 320/768/1366px, keyboard/focus, dark/system và empty state. | Huy |
| P1 | SMTP khi triển khai local chưa cấu hình trong source công khai. | Dùng env cá nhân/SMTP test, không commit credentials, ghi evidence nhận mail. | Duy |
| P1 | Khởi tạo job subprocess bị kill/treo trên Windows chưa test. | Kill process, recovery theo hướng dẫn, bảo đảm không báo COMPLETED giả. | Duy + Quý |

> Các dòng nêu vấn đề **cần kiểm thử hoặc cải tiến** chứ không khẳng định tất cả đều đang lỗi runtime. Riêng phần CSV formula injection và phân quyền gán job là điểm review code phải được khóa test trước release.

## 5. Danh sách 37 test case liên kết với SRS

Đây là **test gate**, chưa phải kết quả Pass/Fail hiện tại. Người được giao điền `Not run`/`Pass`/`Fail` cùng link evidence trong Excel. SRS 4.2 chứa bước test và expected result chính thức.

| TC | Liên kết FR | Người phụ trách theo SRS | Nhóm kiểm tra | Trạng thái E2E |
|---|---|---|---|---|
| TC-01 | `FR-PLT-04` | Duy | Giải nén LTW-TH, chạy START_HERE.bat Windows sạch | `Not run` |
| TC-02 | `FR-PUB-01` | Huy | Guest mở / và CTA | `Not run` |
| TC-03 | `FR-AUT-01` | Duy | Đăng ký email/password hợp lệ | `Not run` |
| TC-04 | `FR-AUT-01` | Duy | Email trùng/invalid/weak password | `Not run` |
| TC-05 | `FR-AUT-02,FR-AUT-08` | Duy | Sai mật khẩu liên tiếp | `Not run` |
| TC-06 | `FR-AUT-03,FR-AUT-09` | Duy | Guest truy cập workspace và logout | `Not run` |
| TC-07 | `FR-AUT-04` | Duy | Reset password local-only có opt-in | `Not run` |
| TC-08 | `FR-AUT-05` | Duy | Cấu hình SMTP thật gửi đến email thử | `Not run` |
| TC-09 | `FR-AUT-06` | Duy | Đổi mật khẩu trong settings | `Not run` |
| TC-10 | `FR-USR-01` | Huy | Đổi VI→EN→VI và refresh | `Not run` |
| TC-11 | `FR-USR-02` | Huy | Dark/light/system + reload | `Not run` |
| TC-12 | `FR-USR-03,FR-USR-04` | Huy | Đổi layout grid/list | `Not run` |
| TC-13 | `FR-USR-05` | Duy | Tạo 2 user A/B rồi lưu sách và bộ lọc | `Not run` |
| TC-14 | `FR-CRW-01,FR-CRW-02` | Duy | Start job max_pages=0,4,"2",1 | `Not run` |
| TC-15 | `FR-CRW-03` | Duy | Hai user tạo job khi có một job active | `Not run` |
| TC-16 | `FR-CRW-05` | Quý | Crawl live max_pages=2 | `Not run` |
| TC-17 | `FR-CRW-06` | Quý | Lấy 2–3 chi tiết sách mẫu live | `Not run` |
| TC-18 | `FR-CRW-04,FR-CRW-07` | Quý | Kiểm tra robots, delay và host allowlist | `Not run` |
| TC-19 | `FR-CRW-08` | Quý | Crawl lại cùng phạm vi | `Not run` |
| TC-20 | `FR-CRW-11` | Quý | Giả lập request fail / parser fail | `Not run` |
| TC-21 | `FR-CRW-12` | Duy | Kill worker giữa RUNNING | `Not run` |
| TC-22 | `FR-CRW-09,FR-CRW-10` | Huy | Start job, reload trong khi chạy | `Not run` |
| TC-23 | `FR-BOO-01,FR-BOO-02` | Huy | Tìm theo từ khóa có và không có kết quả | `Not run` |
| TC-24 | `FR-BOO-03` | Huy | Lọc giá GBP min/max và sai input | `Not run` |
| TC-25 | `FR-BOO-04` | Huy | Mở chi tiết sách và giá lịch sử | `Not run` |
| TC-26 | `FR-BOO-05,FR-BOO-06` | Huy | Bookmark/unbookmark và xem Saved | `Not run` |
| TC-27 | `FR-BOO-07` | Huy | Lưu/xóa filter sau khi refresh | `Not run` |
| TC-28 | `FR-BOO-08` | Duy | Xuất CSV mở bằng Excel | `Not run` |
| TC-29 | `FR-WSP-01` | Huy | DB mới không có sách | `Not run` |
| TC-30 | `FR-WSP-02` | Duy | Lịch sử jobs của A/B và try URL khác | `Not run` |
| TC-31 | `FR-WSP-03` | Huy | Kiểm analytics sau crawl | `Not run` |
| TC-32 | `FR-WSP-04,FR-WSP-05` | Quý | Mở Sources và Help | `Not run` |
| TC-33 | `FR-WSP-06` | Huy | Chrome/Edge 320/768/1366px + keyboard | `Not run` |
| TC-34 | `FR-PLT-01` | Duy | Gửi POST/PATCH thiếu/sai X-CSRF-Token | `Not run` |
| TC-35 | `FR-PLT-02` | Duy | Kiểm session cookie/CSP và Apache url | `Not run` |
| TC-36 | `FR-PLT-03` | Duy | Upgrade bản sao DB V3→V4 | `Not run` |
| TC-37 | `FR-PLT-04` | Quý | Chạy pytest trên máy có Flask/Scrapy | `Not run` |

## 6. Quy trình nghiệm thu thực tế

1. **Nhận baseline:** clone source V4, tạo `.venv`, cấu hình `.env` local an toàn, giữ DB runtime khác với database DEMO.
2. **Chạy automated:** `python -m pytest -q`; ghi environment Python/package, ảnh màn hình và log. Không đánh dấu DONE nếu có skip do thiếu dependency.
3. **DB smoke:** `python -m database.tools.db_cli tables` và `... check`; kiểm migration 001..004, toàn vẹn FK và backup.
4. **Account smoke:** đăng ký A/B, login, CSRF, đổi locale/theme, reset password và logout; xác nhận các đối tượng riêng không lộ nhau.
5. **Crawler smoke:** 1 trang, 2 trang, crawl lại; đối chiếu `books`, `crawl_pages`, `crawl_events`, `crawl_job_books`, `book_price_history`.
6. **Frontend:** DevTools Console/Network, mobile widths, biểu đồ, bộ lọc, saved search, history, empty/loading/error states.
7. **Export & email:** CSV UTF-8/formula safety, SMTP nhận mail, expired/reset-used tokens, không leak token/log.
8. **Handoff:** đính kèm screenshot/log, người review, commit/PR, đánh `QA_PASS` trong Excel; bản release tiếp theo mới chuyển sang `04_transition` để đóng gói/triển khai.

### 6.1. Checklist bàn giao mỗi task

- Có issue/mã FR và người owner.
- Ghi danh sách file sửa; không sửa song song chung file giữa 2 AI Agent khi chưa đồng bộ branch.
- Có test mới/sửa regression phù hợp và log kết quả thực tế.
- API field/database migration không bị đổi ngầm; nếu đổi thì cập nhật API + SRS + Excel cùng PR.
- Có ảnh/video nếu thay đổi UI hoặc luồng crawler.
- Review/merge rồi mới coi là hoàn thành; không tự động chấm %.

## 7. Các chức năng CHƯA có trong V4 (không được tính Done)

- Public production hosting, HTTPS reverse proxy, CDN và distributed crawler.
- OAuth/Google login, xác minh email khi đăng ký, admin/RBAC, tenant/role nâng cao.
- URL crawling tùy ý, đa website tùy chọn, vượt robot policy/CAPTCHA, scheduling/WebSocket/push.
- AI recommendation/tóm tắt sách tự động, quy đổi tiền tệ, dịch nội dung sách.

Muốn thêm, tạo ticket thay đổi scope, đặc tả bảo mật/chức năng, cập nhật SRS và giao người chịu trách nhiệm trước khi code.

## 8. Liên hệ với các pha và tài liệu canon

```text
LTW-TH/docs/
├── 02_elaboration/
│   ├── SRS_CrawlInsight_Consolidated.md
│   ├── API_CrawlInsight_Consolidated.md
│   └── API_CrawlInsight_Consolidated.docx
└── 03_construction/
    ├── IMPLEMENTATION_STATUS_Consolidated.md
    └── IMPLEMENTATION_STATUS_Consolidated.docx
```

- `02_elaboration`: *hệ thống phải làm gì* (SRS) + *các thành phần giao tiếp ra sao* (API contract).
- `03_construction`: *đã code và test đến đâu* (Implementation Status, kỹ thuật, lỗi cần sửa, evidence).
- `04_transition`: *đã release/triển khai/được nghiệm thu chưa* (deployment guide, user acceptance, release note); **chưa phải nơi đặt Implementation Status hiện tại**.
- Các bản `API.md`, `API_V4.md`, `IMPLEMENTATION_STATUS.md`, `IMPLEMENTATION_STATUS_V4.md` là **legacy** sau khi hợp nhất. Có thể đưa `docs/archive/` hoặc chỉ giữ trên Git history; **đừng xóa khi chưa kiểm tra source/commit**.

---

**Cách cập nhật:** người phụ trách sửa Markdown trước, gắn ngày/commit/evidence, rồi xuất Word cùng nội dung. Đây là snapshot code V4, không thay thế bảng kế hoạch và trách nhiệm 90 task trong Excel.
