# Đánh giá sản phẩm và hỏi đáp — 21/10/2026

Hai tab nằm trong trang chi tiết sản phẩm, cạnh tab Thông số. Không nhập dữ liệu người dùng, điểm sao hoặc bình luận minh họa từ ảnh thiết kế.

## Cách sử dụng

- Khách chưa đăng nhập xem nội dung đã duyệt. Đăng nhập để gửi câu hỏi hoặc phản hồi câu hỏi.
- Mỗi tài khoản được gửi một đánh giá cho mỗi sản phẩm, khi có ít nhất một đơn của chính tài khoản chứa sản phẩm, đã COMPLETED và PAID. Áp dụng ở cấp sản phẩm, bao gồm các biến thể. Đánh giá bị ẩn vẫn giữ giới hạn một lần; chưa hỗ trợ sửa/xóa đánh giá phía khách.
- Đánh giá gồm 1–5 sao, tiêu đề tùy chọn, nội dung và tối đa 5 ảnh JPG/PNG/WebP, mỗi ảnh đầu vào tối đa 5 MB/16 megapixel. Backend giải mã, xoay theo EXIF, thu nhỏ tối đa 1200×1200, lưu JPEG đã loại metadata trong FeedbackPhoto. Không chấp nhận HTML/SVG hoặc URL ảnh tùy ý. Ảnh chờ duyệt chỉ chủ bài và admin đọc được; ảnh đã ẩn không còn công khai.
- Đánh giá, câu hỏi và phản hồi của khách mặc định PENDING. Chủ nội dung vẫn thấy nội dung của mình cùng nhãn chờ duyệt; người khác chỉ thấy APPROVED. Điểm trung bình và số sao chỉ tính đánh giá đã duyệt, không tính bài đang chờ/ẩn. Khi chưa có đánh giá, hiển thị dấu “—”, không tạo điểm mặc định.
- Admin mở **Đánh giá & hỏi đáp** tại `/feedback`, duyệt/ẩn/chuyển chờ duyệt, xem báo cáo và trả lời với tư cách TechRetail. Hàng chờ mặc định bao gồm cả bài đã đăng có phản hồi khách đang chờ duyệt. Chỉ superuser đang hoạt động có quyền kiểm duyệt/phản hồi chính thức; quyền bán hàng theo chi nhánh không tự cấp quyền trên nội dung toàn hệ thống.
- Phản hồi chính thức được duyệt tự động, nhưng chỉ xuất hiện công khai sau khi bài gốc được duyệt. Nhãn nhân viên do backend quyết định, không lấy từ dữ liệu khách gửi.
- Có bộ lọc số sao, ảnh, sắp xếp mới nhất/hữu ích; hỏi đáp có tìm kiếm và lọc đã/chưa được TechRetail trả lời. Danh sách phân trang 20 dòng, tối đa 100 theo API. Khách đăng nhập có thể đánh dấu hữu ích hoặc báo cáo bài đã đăng. Phiếu hữu ích/báo cáo duy nhất theo tài khoản và bài; báo cáo chỉ admin đọc được.

## API và bảo vệ dữ liệu

- GET/POST `products/{slug}/feedback/`: `kind=REVIEW|QUESTION`, `rating`, `photos=true`, `sort=helpful`, `search`, `answered=true|false`, `page`. GET trả results, summary, viewer; POST nhận JSON hoặc multipart khi có ảnh.
- POST `feedback/{id}/replies/`: body chứa body. Khách chỉ phản hồi câu hỏi đã duyệt; admin có thể trả lời cả đánh giá và câu hỏi.
- PUT `feedback/{id}/helpful/`: `{helpful: true|false}`, thao tác đặt trạng thái thay vì đảo trạng thái để retry không cộng trùng.
- POST `feedback/{id}/report/`: `{reason: ...}`.
- GET `feedback/photos/{id}/`: JPEG, có kiểm tra quyền và trạng thái bài gốc.
- GET `feedback-admin/`: quản trị; lọc kind, status, reported và search.
- PATCH `feedback-admin/{id}/` hoặc `feedback-admin/replies/{id}/`: `{status: PENDING|APPROVED|HIDDEN}`.

Mọi thao tác ghi tiếp tục dùng session cookie/CSRF đang có, không thêm JWT hoặc cơ chế phiên khác. Gửi bài, phản hồi, báo cáo giới hạn 10/phút theo tài khoản, ngoài giới hạn API chung. Backend tự gắn chủ bài, đơn đã mua và trạng thái; các trường giả mạo author/status/is_staff_reply không cấp quyền. Phản hồi không chứa email, điện thoại, mã đơn hoặc ID tài khoản. Tên công khai lấy full_name, nếu chưa đặt tên hiển thị “Khách hàng”. React hiển thị nội dung dạng text, không render HTML người dùng. Audit lưu mã thao tác/trạng thái, không sao chép nội dung hoặc ảnh.

Ảnh lưu trong database nên cần tính dung lượng sao lưu khi vận hành. Thiết kế hiện tại phù hợp phạm vi đồ án; chưa có thông báo email/push và chưa tách ảnh sang object storage.

## Cài đặt và kiểm tra

Đã bổ sung Pillow vào requirements và hai migration products/0002,0003. Trên máy khác, cài lại requirements, chạy migrate rồi khởi động lại backend. Không có data migration/seed nội dung người dùng.

```powershell
Set-Location -LiteralPath 'F:\OneDrive\Documents\VPProjects\đồ án\tech-retail-system'
.\.venv\Scripts\python.exe -m pip install -r .\be\requirements.lock.txt
Set-Location .\be
..\.venv\Scripts\python.exe manage.py migrate
```

Kiểm thử tự động chạy trên test_tech_retail, không tạo đơn, đánh giá, tài khoản hoặc ảnh thử trên database vận hành. `be/tests/test_feedback.py` kiểm tra quyền mua hàng, chống đánh giá trùng, kiểm duyệt/ẩn, tính sao, ảnh/metadata, CSRF, giới hạn gửi, phân trang và hữu ích/báo cáo. `shared/ProductCommunity.test.jsx` kiểm tra trạng thái trống, gửi multipart, lỗi mạng, nhãn nhân viên, đổi tài khoản và thao tác admin. `shared/api.test.jsx` kiểm tra multipart giữ CSRF/cookie và không tự đặt Content-Type làm hỏng boundary.

## File triển khai và kiểm chứng trình duyệt

- Backend: products/models.py, products/feedback.py, products/migrations/0002 và 0003, config/urls.py; settings.py bổ sung throttle feedback. Dependency Pillow được khóa trong requirements.
- Khách hàng: ProductDetail.jsx tích hợp ProductCommunity.jsx/CSS, giữ nội dung thông số hiện có. shared/api.js bổ sung gửi FormData cùng cơ chế CSRF hiện tại.
- Admin: FeedbackPage.jsx/CSS, route /feedback và mục menu Đánh giá & hỏi đáp.
- Đã áp dụng migration tạo bảng và khởi động lại các dịch vụ local. Kiểm tra trực tiếp database ứng dụng sau triển khai: ProductFeedback=0, FeedbackReply=0, FeedbackPhoto=0; không seed dữ liệu mẫu.
- Trình duyệt desktop đã mở sản phẩm, xem tab Đánh giá/Hỏi đáp, thấy trạng thái trống, điều kiện chưa đủ để đánh giá của tài khoản hiện tại, form hỏi đáp và màn hình admin trống. Ảnh tại screenshots/product-reviews-empty-desktop.png, product-questions-empty-desktop.png, product-questions-empty-full-desktop.png và product-feedback-admin-empty.png.
- Chưa nghiệm thu thao tác gửi/duyệt đầy đủ bằng trình duyệt, vì không tạo nội dung thử trong tài khoản/database ứng dụng. Luồng này đã được kiểm thử API trên database riêng, bao gồm cùng một cookie jar đăng nhập khách/admin, gửi ảnh multipart với CSRF, khách bị từ chối kiểm duyệt, admin duyệt và khách đọc kết quả.
- Chưa xác minh trực quan mobile: công cụ viewport nhận yêu cầu 390px nhưng sau tải lại trang vẫn báo 1265px; đã khôi phục viewport mặc định, không coi ảnh desktop là ảnh mobile. CSS có breakpoint 950px/550px, cần kiểm tra thêm trên điện thoại thực tế.

Kết quả cuối: **217 backend tests PASS** trên test_tech_retail (19 ca feedback), **91 Vitest tests PASS** (10 ca giao diện feedback và ca multipart bổ sung), **4 Node tests PASS**. Build fe/admin, OpenAPI validate không cảnh báo, Django check, migration drift, Ruff/Prettier và git diff --check đều qua. Không có giao dịch thanh toán hoặc đăng nhập provider thật trong lần kiểm thử này.
