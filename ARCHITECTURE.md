# Kiến trúc hệ thống

## Khảo sát trước triển khai

Workspace ban đầu chỉ có `uc/*.jpg`, `class/class.jpg`; thư mục Database Diagram và Sequence Diagram chưa có file. Đã đọc sơ đồ tổng quan, sơ đồ lớp và các sơ đồ UC được cung cấp. Chưa có SRS văn bản hoặc mã nguồn/migration. Mã chức năng F01–F19 trong traceability là mã tạm, không giả định là ID UC chính thức.

Sơ đồ UC có tác nhân cổng thanh toán, AI, đăng nhập bắt buộc khi đặt hàng. Prompt hiện tại ưu tiên COD/tiền mặt/chuyển khoản thủ công, guest checkout, OAuth/Gemini DEFERRED. Vì đây là khác biệt phạm vi đã được prompt quyết định rõ, không triển khai cổng thanh toán ngoài. RelatedProductLink trên UML chưa cần cho nghiệp vụ hiện tại. Manufacturer ánh xạ Brand; Branch ánh xạ Store. ShippingDetails được nhúng trong snapshot Order; quyền dùng Group/Permission Django và RoleAssignment theo chi nhánh thay vì nguồn quyền thứ hai.

## Quyết định thiết kế

Hai React/Vite JavaScript app trên 5173 (khách) và 5174 (nhân viên), cùng API Django REST `/api/v1` trên 8000. Vite proxy `/api` để cookie/CSRF hoạt động cùng origin; CORS chỉ cho hai origin cụ thể. MySQL InnoDB utf8mb4, isolation READ COMMITTED, timezone nghiệp vụ Asia/Ho_Chi_Minh. Không có backend Node hoặc dịch vụ trung gian.

Custom user email chuẩn hóa lowercase, Django password hashing/session HttpOnly; CSRF cả login và request ẩn danh thay đổi dữ liệu. Group/Permission là nguồn quyền duy nhất, RoleAssignment gán group với Store. Superuser toàn chuỗi; nhân viên chỉ có quyền group của assignment trong chi nhánh tương ứng. Truy vấn list/detail/export phải lọc scope trước. Customer chỉ xem profile/order sở hữu; không ghép khách theo điện thoại.

Mỗi dòng JSON -> Product + Variant, không gộp bằng tên. Snapshot JSON giữ nguyên; namespace + source ID unique, SKU unique. Slug nội bộ có hậu tố source ID khi trùng. Brand chỉ trim/collapse whitespace; Apple và Apple Chính hãng vẫn tách biệt. Specs tách theo ` | `, `:` đầu tiên, giữ chuỗi gốc; chỉ chuẩn hóa số khi khớp toàn bộ mẫu và đơn vị rõ ràng.

Mỗi chi nhánh nguồn có kho mặc định, không bịa địa chỉ/điện thoại. Tồn bootstrap ghi StockMovement INITIAL; import lại cập nhật catalog nhưng giữ giá/tồn vận hành. Tất cả thay đổi kho qua services atomic, khóa warehouse tăng dần rồi balance tăng variant ID. Warehouse lock bảo vệ cả trường hợp balance chưa tồn tại. Điều này chủ ý tuần tự hóa giao dịch cùng kho, phù hợp quy mô đồ án và tránh race tạo balance. Không CRUD số dư.

Checkout khóa kho, lấy giá Decimal từ Variant, tạo Order/items/reservations trong một transaction. Idempotency key thuộc session hoặc user, hash payload; cùng key khác nội dung -> 409. Thời gian bảo lưu key ít nhất vòng đời đơn; không tự xóa. PENDING hết hạn hủy và giải phóng; confirmed không hết hạn theo TTL pending. POS draft không giữ; finish kiểm tra lại tồn, thu tiền, xuất kho, tạo invoice atomic.

Kho thực tế và giữ chỗ độc lập: available=on_hand-reserved. Dispatch transfer tiêu thụ reservation nguồn; hàng IN_TRANSIT tính từ transfer items, nằm ngoài hai kho. Receive toàn bộ một lần. Online ship xuất kho một lần. Payment thu/hoàn thủ công unique key, snapshot amount; invoice one-to-one không có hiệu ứng kho/tiền. Audit không chứa OTP/token/password/chat.

API chatbot trả 503 AI_NOT_CONFIGURED. Retrieval lọc catalog trong MySQL và trả dữ liệu đã kiểm chứng, không gọi Gemini. Chat chỉ ở React state. OAuth tắt, không SDK/credentials giả.

## Ranh giới transaction và báo cáo

Atomic: import toàn file; checkout; mỗi chuyển trạng thái; post chứng từ; approve/dispatch/receive/cancel transfer; thu/hoàn; finish POS. Khóa theo kho rồi đối tượng nguồn; service khóa lại và kiểm tra trạng thái trong transaction. DB constraints là lớp bảo vệ cuối. Errors trả code/message/fields/request_id, không trả secrets/stacktrace.

Doanh thu bán = tổng grand_total đơn COMPLETED có paid_at, theo completed_at, trừ giao dịch REFUND theo ngày hoàn. Thu tiền = CAPTURE - REFUND theo created_at. Không tính lợi nhuận. Lọc ngày [đầu ngày, đầu ngày kế tiếp) theo timezone nghiệp vụ và scope; export cùng queryset, chống CSV formula injection.

## Phạm vi

Làm ngay: tài khoản, catalog/import, chi nhánh/kho, nhà cung cấp, nghiệp vụ kho/điều chuyển, giỏ hàng, online/POS, tiền thủ công, OTP, invoice, báo cáo, audit, hai UI. Deferred: Google/Facebook/Gemini và delivery email/SMS thật. Ngoài phạm vi: tự động thanh toán/đối soát, thuế/hóa đơn điện tử, loyalty, vận chuyển, đầy đủ bảo hành/đổi trả.
