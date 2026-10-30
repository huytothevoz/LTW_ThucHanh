# PHÂN CÔNG CÔNG VIỆC CÒN LẠI — CRAWLINSIGHT

## Mục tiêu chung

- Hoàn thiện CrawlInsight với **Laravel/PHP là backend chính**, **Python/Scrapy là crawler**, và hai phần dùng chung MySQL/MariaDB trên cổng XAMPP 3308.
- Ưu tiên xử lý các hạng mục chưa được chạy kiểm thử thực tế trước khi bổ sung tính năng mới.
- Mỗi thành viên cập nhật trạng thái và lưu minh chứng kiểm thử sau khi hoàn thành công việc.

## 1. Võ Trịnh Quốc Huy — Giao diện và trải nghiệm người dùng

- Kiểm tra các trang chính: trang chủ, đăng ký/đăng nhập, workspace, danh sách sách, sách đã lưu, lịch sử crawl, phân tích, nguồn dữ liệu và cài đặt.
- Chạy ứng dụng trên trình duyệt sau khi môi trường backend được cài đặt; sửa các lỗi giao diện hoặc thao tác phát sinh.
- Kiểm tra luồng giao diện gọi API: trạng thái tải, thông báo thành công/thất bại, dữ liệu rỗng và lỗi khi phiên đăng nhập hết hạn.
- Kiểm tra giao diện tiếng Việt/tiếng Anh, chế độ sáng/tối và khả năng hiển thị trên màn hình điện thoại.
- Kiểm tra các luồng người dùng:
  - Đăng ký, đăng nhập và đăng xuất.
  - Khởi chạy crawl, theo dõi trạng thái và xem lịch sử.
  - Tìm kiếm/lọc sách, lưu và bỏ lưu sách hoặc bộ lọc.
  - Cập nhật hồ sơ và tùy chọn cá nhân.
- Ghi lại ảnh chụp màn hình và các bước tái hiện cho lỗi giao diện; cập nhật tài liệu hướng dẫn sử dụng khi giao diện thay đổi.
- Phát triển thêm sau khi các luồng hiện tại ổn định:
  - Cải thiện khả năng tiếp cận: nhãn biểu mẫu, điều hướng bằng bàn phím, độ tương phản và thông báo dễ hiểu.
  - Bổ sung trạng thái tiến trình crawl rõ ràng, thao tác thử lại khi phù hợp và hướng dẫn xử lý lỗi cho người dùng.

## 2. Phạm Ngọc Duy — Backend Laravel/PHP, API và bảo mật

- Cài đặt PHP 8.2+ và Composer trên máy phát triển; chạy `composer install`, kiểm tra PHP syntax và khởi động Laravel.
- Chạy PHPUnit; bổ sung/sửa test cho API và các luồng nghiệp vụ trước khi xác nhận backend hoạt động.
- Kiểm thử API bằng HTTP thực tế:
  - Đăng ký, đăng nhập, đăng xuất và xác thực phiên.
  - CSRF cho các thao tác thay đổi dữ liệu; quyền truy cập của khách và người dùng đã đăng nhập.
  - Cập nhật hồ sơ, mật khẩu, tùy chọn, bookmarks và saved searches.
  - Sở hữu dữ liệu theo tài khoản; người dùng không được đọc hoặc sửa dữ liệu của tài khoản khác.
  - Tạo crawl job, kiểm tra xung đột khi có job đang chạy, trạng thái và lịch sử.
  - Xuất CSV với dữ liệu tiếng Việt và ô bắt đầu bằng ký tự có thể gây CSV formula injection.
- Xác minh tài khoản cũ có thể đăng nhập bằng mật khẩu scrypt đã tạo từ backend Python; nếu không tương thích, sửa theo hướng giữ khả năng đăng nhập và có kế hoạch nâng cấp hash an toàn.
- Kiểm tra luồng quên/đặt lại mật khẩu, thời hạn và khả năng dùng một lần của token, cấu hình SMTP và cách xử lý lỗi gửi thư.
- Rà soát lỗi API, validation, rate limit, session/cookie và security headers; không đưa secret hoặc thông tin nhạy cảm vào phản hồi/log.
- Phát triển thêm sau khi kiểm thử nền tảng đạt:
  - Bổ sung API tests cho các trường hợp biên và lỗi.
  - Chuẩn hóa thông báo lỗi và tài liệu hợp đồng API khi có thay đổi.
  - Đánh giá hiệu năng các truy vấn tìm kiếm, dashboard và analytics trước khi tối ưu.

## 3. Nguyễn Trọng Quý — Crawler, MySQL và tích hợp/chạy thử

- Kiểm tra cấu hình để Laravel và Python worker cùng dùng `DB_HOST`, `DB_PORT`, `DB_DATABASE`, `DB_USERNAME` và `DB_PASSWORD`.
- Chạy kiểm tra MySQL/MariaDB trên cổng 3308; xác minh schema, foreign keys, import SQLite cũ và backup.
- Chạy crawler thật với giới hạn nhỏ trên nguồn sandbox được phép; xác minh job được tạo, worker khởi chạy, log được ghi, sự kiện/trạng thái cập nhật và dữ liệu sách được lưu.
- Kiểm tra xử lý lỗi và khôi phục job khi worker dừng bất thường; xác minh không để lại job hoạt động bị treo hoặc tạo hai job trái quy định.
- Kiểm thử `START_HERE.bat`, `scripts/setup_windows.ps1`, `scripts/start_windows.ps1` và `scripts/run_tests_windows.ps1` trên Windows có PHP, Composer và Python phù hợp.
- Kiểm tra cài đặt sạch từ hướng dẫn/ZIP, kết nối XAMPP MySQL khi dự án nằm trong hoặc ngoài `htdocs`, và bảo đảm `.env` không bị phục vụ công khai.
- Thực hiện diễn tập sao lưu và phục hồi database trên bản sao; ghi lại lệnh, kết quả và các bước xử lý lỗi thường gặp.
- Phát triển thêm sau khi tích hợp hiện tại ổn định:
  - Cải thiện khả năng quan sát job: log dễ đọc, thông tin lỗi hữu ích và tiến độ nhất quán.
  - Bổ sung kiểm tra dữ liệu crawler trước khi lưu và kiểm thử hồi quy cho parser.
  - Đánh giá chính sách crawl có trách nhiệm: giới hạn tốc độ, phạm vi domain và tuân thủ `robots.txt`.

## 4. Công việc chung của cả nhóm

- Cùng thiết lập môi trường PHP/Composer/Python và xử lý các lỗi cài đặt; lưu lại phiên bản công cụ đã dùng.
- Không đánh dấu chức năng là hoàn tất chỉ dựa trên việc có mã nguồn: phải chạy và lưu kết quả kiểm thử tương ứng.
- Trước khi gộp thay đổi:
  - Chạy `scripts/run_tests_windows.ps1` và xử lý các lỗi liên quan.
  - Kiểm tra thay đổi không làm sai hợp đồng API, schema MySQL hoặc luồng giao diện.
  - Không commit `.env`, mật khẩu MySQL/SMTP, khóa ứng dụng, database thật hoặc dữ liệu cá nhân.
- Trước buổi nghiệm thu:
  - Chạy thử toàn bộ luồng từ tạo tài khoản đến crawl và xem dữ liệu.
  - Chuẩn bị dữ liệu demo phi định danh, ảnh chụp màn hình và kịch bản dự phòng.
  - Đồng bộ README, tài liệu cài đặt, kiến trúc, API và trạng thái kiểm thử theo kết quả thực tế.

## 5. Hạng mục phát triển thêm sau khi hoàn tất kiểm thử nền tảng

- Cải thiện tìm kiếm và bộ lọc sách; đánh giá hiệu năng trên dữ liệu có kích thước tăng dần.
- Bổ sung biểu đồ hoặc bộ lọc thời gian cho analytics khi dữ liệu hiện có hỗ trợ.
- Hoàn thiện lịch sử biến động giá và thông tin nguồn/thời điểm thu thập để người dùng hiểu ngữ cảnh dữ liệu.
- Cải thiện khả năng tiếp cận và trải nghiệm trên thiết bị di động.
- Chỉ cân nhắc triển khai các tính năng mới sau khi nhóm đã thống nhất phạm vi, tiêu chí nghiệm thu và ảnh hưởng tới API/database.
