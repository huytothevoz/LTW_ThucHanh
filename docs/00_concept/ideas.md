# CrawlInsight — Ý tưởng sản phẩm (chốt theo SRS 2.0)

**Đề giữa kỳ 7 — Web Crawling, môn Lập trình Web & Ứng dụng 503073.**  
**Bản đồng bộ:** 2026-10-21 · 10-day scope. Phần ý tưởng A + một phần C từ tài liệu cũ đã được thu gọn. Nếu có mâu thuẫn, `SRS_CrawlInsight_10Days.md` là tài liệu chính.

## 1. Bài toán

Thông tin sách trên web xuất hiện dưới dạng nhiều trang HTML liên kết với nhau và khó lọc/thống kê hàng loạt. Nhóm làm hệ thống web giúp **chạy và quan sát một lượt crawling thật**, chuyển dữ liệu HTML trên website sandbox thành bản ghi có cấu trúc trong SQLite và tìm kiếm, thống kê trên dữ liệu này.

## 2. Hướng chọn: A + một phần C

- **A — Book Crawling & Analytics:** catalogue sách, tìm kiếm tên, lọc khoảng giá, biểu đồ số sách theo ratings.
- **C — Crawl Monitor rút gọn:** nút chạy crawl theo giới hạn catalogue pages, trạng thái PENDING/RUNNING/COMPLETED/FAILED, counters, lịch sử 5 job.
- **Không biến** thành nền tảng crawlers nhiều website, không xây analytics đa biểu đồ, không đăng nhập, không dùng AI, không so sánh giá theo thời gian.

## 3. Product journey

1. Người vận hành mở Dashboard, thấy kho sách rỗng nếu chưa crawl.
2. Chọn 1–3 trang catalogue từ nguồn cố định Books to Scrape và nhấn Start.
3. Flask ghi job vào SQLite, chạy child process Scrapy, UI theo dõi bằng HTTP polling.
4. Spider theo link detail/Next, tôn trọng robots và tốc độ, trích xuất 6 trường chính, upsert chống trùng.
5. Người dùng xem tổng sách, rating chart, job stats và Book Explorer.
6. Nếu chạy lại cùng phạm vi, kho sách không bị nhân đôi.

## 4. Giá trị học thuật

- Chứng minh sự khác biệt giữa crawling (di chuyển qua mạng link) và scraping (trích xuất dữ liệu từ HTML).
- Biết sử dụng HTTP, CSS selectors, HTML DOM, structured data, SQLite transaction, error handling, API và asynchronous process.
- Nhận thức về robots.txt, giới hạn tốc độ và đạo đức dữ liệu.
- Đánh giá năng lực bằng evidence thật: logs, browser Network, hình UI, SQL results, repeat-crawl dedup và automated tests.

## 5. Thiết kế và công nghệ

- **UI:** HTML/Jinja + CSS responsive + Vanilla JS, không CDN; Dashboard và Book Explorer.
- **Backend:** Flask routes + JSON API; dữ liệu SQLite 2 bảng.
- **Crawler:** Python Scrapy ở child process độc lập.
- **Nền tảng:** Windows 10/11 local; Python 3.11/3.12; không cần XAMPP.
- **Thẩm mỹ:** bố cục dễ dùng với navigation cố định, header rõ ràng, dark sidebar + clean content, empty/loading/error states, không dùng số ảo.

## 6. Mức độ thành công

Chỉ coi MVP đạt khi live crawler đi từ catalogue sang detail và Next, lưu dữ liệu thật, hiện ở web, filter hoạt động, trạng thái job đúng và crawl lặp không tạo trùng. Một UI đẹp mà không có crawling thật không đạt yêu cầu.

**Chi tiết triển khai:** `SRS_CrawlInsight_10Days.md`, `docs/ARCHITECTURE.md`, `docs/API.md` và `docs/IMPLEMENTATION_STATUS.md`.
