# KẾ HOẠCH VÀ TỔNG HỢP NHIỆM VỤ (TASK SUMMARY)

**Thành viên:** Phạm Ngọc Duy  
**Chuyên ngành:** Mạng máy tính & Truyền thông dữ liệu  
**Trọng tâm phụ trách:** Backend Flask, API Endpoints, Database SQLite & An toàn bảo mật  
**Dự án:** CrawlInsight (Web Crawling & Book Data Analytics Platform) — Đề tài 07 (503073)  

---

## 1. Ranh giới trách nhiệm & Module sở hữu (Code Ownership)

| Khu vực | Files / Thư mục sở hữu | Trách nhiệm chính |
|---|---|---|
| **Flask Core & App** | `app.py` | Quản lý cấu hình `.env`, session lifetime, context processor, error handlers, khởi chạy process crawler. |
| **Bảo mật & Session** | `src/web/security.py`, `src/web/auth.py` | CSRF guard (`X-CSRF-Token`), rate-limiting chống brute-force, hash mật khẩu (`scrypt`), session versioning để revoke phiên cũ. |
| **Email & Khôi phục** | `src/web/mail.py` | Kết nối SMTP gửi mail khôi phục mật khẩu, token TTL/one-time use, chế độ fallback an toàn khi lỗi SMTP. |
| **Workspace API** | `src/web/workspace.py` | Các API bảo vệ: `/api/summary`, `/api/books`, `/api/bookmarks`, `/api/saved-searches`, `/api/history`, xuất CSV UTF-8 BOM an toàn. |
| **Database & Migrations**| `src/database/*.py`, `database/migrations/*` | 15 bảng, 3 views, SQLite WAL mode, foreign keys, additive migration 001–004, script sao lưu & phục hồi dữ liệu. |
| **Môi trường & Cách ly** | `START_HERE.bat`, `scripts/*`, `.htaccess` | Cách ly dữ liệu ngoài XAMPP Apache `htdocs`, ngăn ngừa rò rỉ `.env` và file `.sqlite3`. |

---

## 2. Bảng phân công công việc chi tiết (10-Day Plan)

*Dữ liệu trích xuất trực tiếp từ bảng phân công nhiệm vụ đề tài (`docs/LTW-TH_PhanCong.xlsx`).*

### Giai đoạn 1: Thiết lập môi trường & Nền tảng dữ liệu (Day 1 - Day 3)
| Mã Task | Ưu tiên | Yêu cầu (FR/NFR) | Nội dung công việc | Minh chứng nghiệm thu cần đạt | Trạng thái |
|---|---|---|---|---|---|
| **TK-004** | P0 | FR-PLT-04 | Setup môi trường Windows sạch: cài Python venv, pip install, chạy thử Flask local | Log cài đặt thành công, server lắng nghe tại `127.0.0.1:5000` | Chưa bắt đầu |
| **TK-005** | P0 | FR-PLT-03 | Kiểm tra database runtime V4: đọc 15 bảng, 3 views, `user_version=4`, `PRAGMA integrity_check` | Output SQL kiểm tra toàn vẹn, FK check = 0 | Chưa bắt đầu |
| **TK-006** | P0 | FR-PLT-02 | Kiểm tra dự án dưới Apache XAMPP: xác nhận SQLite và file `.env` không bị truy cập trực tiếp | Log HTTP 403 / denied khi truy vấn file nhạy cảm từ Apache | Chưa bắt đầu |
| **TK-013** | P0 | FR-AUT-01, FR-AUT-02 | E2E đăng ký, validation dữ liệu, kiểm tra trùng lặp email, đăng nhập/đăng xuất với cookie | Bằng chứng HTTP 201/400/401/200, user tạo mới đúng trong DB | Chưa bắt đầu |
| **TK-014** | P0 | FR-AUT-09, FR-PLT-01 | Kiểm tra bảo vệ CSRF trên mutation APIs (POST/PATCH/DELETE) và các route cần login | Request thiếu token trả 403, guest truy cập trả 401 | Chưa bắt đầu |
| **TK-015** | P0 | FR-USR-05 | Viết smoke test kiểm tra cô lập đa người dùng (Multi-user Isolation) giữa tài khoản A và B | Test PASS: User B không xem/sửa được bookmarks, filters, jobs của A | Chưa bắt đầu |
| **TK-022** | P0 | FR-CRW-01, FR-CRW-03 | E2E crawl job API: tạo job gắn `user_id`, chặn job thứ 2 trả về 409 Conflict | Job thuộc đúng user, hệ thống đảm bảo duy nhất 1 job active | Chưa bắt đầu |
| **TK-023** | P0 | FR-CRW-09 | Kiểm tra tiến trình job và bảng nhật ký sự kiện (`crawl_events`) trong quá trình spider chạy | Counters cập nhật nhất quán, terminal state ghi nhận chính xác | Chưa bắt đầu |
| **TK-024** | P0 | FR-PLT-03 | Kiểm tra migration nâng cấp dữ liệu từ V3 lên V4 trên bản sao DB | Dữ liệu cũ giữ nguyên, file backup tự động tạo, FK check OK | Chưa bắt đầu |

### Giai đoạn 2: Nghiệp vụ Workspace & Bảo mật nâng cao (Day 4 - Day 6)
| Mã Task | Ưu tiên | Yêu cầu (FR/NFR) | Nội dung công việc | Minh chứng nghiệm thu cần đạt | Trạng thái |
|---|---|---|---|---|---|
| **TK-031** | P0 | FR-BOO-05 | Kiểm thử API Bookmarks cross-user: thêm/xóa bookmark, thử book ID không tồn tại | Phân quyền triệt để giữa các user, mã lỗi 404/200 chính xác | Chưa bắt đầu |
| **TK-032** | P1 | FR-BOO-07 | Kiểm thử validation lưu bộ lọc tìm kiếm: trùng tên, range giá không hợp lệ, xóa đúng chủ sở hữu | HTTP 400 khi dữ liệu sai; User B không xóa được filter của User A | Chưa bắt đầu |
| **TK-033** | P1 | FR-BOO-08 | Rà soát xuất file CSV: mã hóa UTF-8 BOM, kiểm tra và ngăn chặn CSV Formula Injection (`=`, `+`, `-`, `@`) | File CSV mở bằng Excel hiển thị tiếng Việt chuẩn, không thực thi mã độc | Chưa bắt đầu |
| **TK-040** | P0 | FR-AUT-04 | Kiểm thử chu trình reset mật khẩu: token TTL (20 phút), token chỉ dùng 1 lần, hủy phiên cũ | Token hết hạn / dùng lại bị từ chối; session cũ lập tức bị revoke | Chưa bắt đầu |
| **TK-041** | P1 | FR-AUT-05 | Tích hợp gửi email SMTP thực tế (Google App Password) & xử lý khi SMTP mất kết nối | Gửi nhận email thành công; khi lỗi trả về thông báo an toàn, không leak secret | Chưa bắt đầu |
| **TK-042** | P0 | FR-PLT-02 | Rà soát toàn diện HTTP Security Headers (CSP, HttpOnly, SameSite=Lax, X-Frame-Options) | Đầy đủ headers bảo mật trên mọi response; không rò rỉ session key | Chưa bắt đầu |
| **TK-049** | P0 | FR-AUT-08, FR-PLT-01 | Cổng kiểm thử an ninh tổng hợp (Security Integration Gate): Brute-force rate limit, CSRF, auth guard | Chặn brute-force sau số lần thử nhất định; phiên bảo mật an toàn | Chưa bắt đầu |
| **TK-050** | P0 | FR-WSP-02 | Kiểm tra hiển thị lịch sử crawl: phân tách giữa 2 user và xử lý dữ liệu legacy (`user_id IS NULL`) | User chỉ thấy job của chính mình; chi tiết job người khác trả 404 | Chưa bắt đầu |
| **TK-051** | P0 | FR-PLT-04 | Đóng băng hợp đồng API & Database: bảo đảm schema V4 ổn định, chuẩn bị migration 005 nếu phát sinh | Hợp đồng API không bị thay đổi bất ngờ làm vỡ giao diện Frontend | Chưa bắt đầu |

### Giai đoạn 3: Tối ưu hóa, Báo cáo & Nghiệm thu (Day 7 - Day 10)
| Mã Task | Ưu tiên | Yêu cầu (FR/NFR) | Nội dung công việc | Minh chứng nghiệm thu cần đạt | Trạng thái |
|---|---|---|---|---|---|
| **TK-058** | P0 | FR-PLT-03 | Diễn tập sao lưu và phục hồi cơ sở dữ liệu (Backup/Restore drill) | Khôi phục bản sao DB thành công, dữ liệu toàn vẹn | Chưa bắt đầu |
| **TK-059** | P0 | FR-PLT-04 | Soạn thảo tài liệu hướng dẫn thiết lập và xử lý sự cố cho lập trình viên / người chấm điểm | Hướng dẫn rõ ràng, cài đặt từ môi trường sạch không phát sinh lỗi | Chưa bắt đầu |
| **TK-060** | P1 | NFR-07 | Đo đạc hiệu năng API tại môi trường local (thử nghiệm với tập dữ liệu 100 và 1000 bản ghi) | Bảng số liệu thời gian phản hồi thực tế (response time) | Chưa bắt đầu |
| **TK-067** | P0 | NFR-05 | Soạn thảo báo cáo kỹ thuật phần Backend, Bảo mật & Cơ sở dữ liệu V4 | Sơ đồ kiến trúc xác thực, sơ đồ ERD 15 bảng, danh mục API | Chưa bắt đầu |
| **TK-068** | P1 | NFR-17 | Chuẩn bị bằng chứng kiểm tra DB (Database Explorer Demo) với dữ liệu phi định danh | Bằng chứng kiểm tra cơ sở dữ liệu hợp lệ | Chưa bắt đầu |
| **TK-069** | P1 | FR-AUT-05 | Hoàn thiện tài liệu hướng dẫn cấu hình SMTP và lưu ý an toàn môi trường phát triển | File hướng dẫn cấu hình chi tiết, không lưu mật khẩu cứng | Chưa bắt đầu |
| **TK-076** | P0 | NFR-05 | Rà soát cấu hình an ninh trước khi đóng gói bản release (tắt debug, tắt local reset link) | Mã nguồn sạch, không hardcode credentials / secret keys | Chưa bắt đầu |
| **TK-077** | P0 | NFR-02 | Kiểm tra tính nhất quán dữ liệu trước release (`PRAGMA foreign_key_check`, `integrity_check`) | DB không có lỗi vỡ khóa ngoại hay phân mảnh dữ liệu | Chưa bắt đầu |
| **TK-078** | P0 | NFR-06 | Kiểm thử cài đặt dự án từ file ZIP sạch trên môi trường Windows mới hoàn toàn | Chạy thành công chỉ với `START_HERE.bat` | Chưa bắt đầu |
| **TK-085** | P0 | NFR-05 | Cổng nghiệm thu bảo mật (Security Release Gate) | Toàn bộ kiểm thử auth/security đạt trạng thái PASS | Chưa bắt đầu |
| **TK-086** | P0 | NFR-02 | Cổng nghiệm thu Database & Migration | Toàn bộ migration và ràng buộc DB kiểm tra đạt chuẩn | Chưa bắt đầu |
| **TK-087** | P0 | NFR-06 | Chuẩn bị kịch bản và dữ liệu dự phòng phục vụ demo trực tiếp | Hệ thống vận hành ổn định, sẵn sàng trình diễn đồ án | Chưa bắt đầu |

---

## 3. Danh mục Test Cases chịu trách nhiệm chính

Phạm Ngọc Duy chịu trách nhiệm trực tiếp về mặt kỹ thuật và cung cấp bằng chứng cho **17 Test Cases**:

- **Môi trường & Nền tảng:** `TC-01` (Setup Windows), `TC-35` (Security Headers / Cookies / Chặn Apache), `TC-36` (Database Upgrade V3→V4).
- **Xác thực & Danh tính:** `TC-03` (Đăng ký thành công), `TC-04` (Validation lỗi đăng ký), `TC-05` (Rate limit brute-force), `TC-06` (Chặn Guest & Logout), `TC-07` (Reset password token), `TC-08` (Gửi mail qua SMTP), `TC-09` (Đổi mật khẩu trong Settings).
- **Bảo mật & Cô lập dữ liệu:** `TC-13` (Multi-user Isolation cho Bookmarks & Search), `TC-30` (Cô lập Lịch sử Crawl Jobs), `TC-34` (Bảo vệ CSRF).
- **Điều phối Crawler:** `TC-14` (Validation `max_pages`), `TC-15` (Chặn chạy 2 jobs đồng thời - 409 Conflict), `TC-21` (Xử lý và khôi phục job bị treo/ngắt đột ngột).
- **Dữ liệu & Xuất file:** `TC-28` (Xuất file CSV chuẩn UTF-8 BOM, an toàn injection).

---

