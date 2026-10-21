# Kiến trúc hệ thống

## Khảo sát trước triển khai

Workspace ban đầu chỉ có `uc/*.jpg`, `class/class.jpg`; thư mục Database Diagram và Sequence Diagram chưa có file. Đã đọc sơ đồ tổng quan, sơ đồ lớp và các sơ đồ UC được cung cấp. Chưa có SRS văn bản hoặc mã nguồn/migration. Mã chức năng F01–F19 trong traceability là mã tạm, không giả định là ID UC chính thức.

Sơ đồ UC có tác nhân cổng thanh toán, AI, đăng nhập bắt buộc khi đặt hàng. Prompt hiện tại ưu tiên COD/tiền mặt/chuyển khoản thủ công, guest checkout, OAuth/Gemini DEFERRED. Vì đây là khác biệt phạm vi đã được prompt quyết định rõ, không triển khai cổng thanh toán ngoài. RelatedProductLink trên UML chưa cần cho nghiệp vụ hiện tại. Manufacturer ánh xạ Brand; Branch ánh xạ Store. ShippingDetails được nhúng trong snapshot Order; quyền dùng Group/Permission Django và RoleAssignment theo chi nhánh thay vì nguồn quyền thứ hai.

## Quyết định thiết kế

Cập nhật theo yêu cầu người dùng ngày 19/10/2026: đặt hàng online và xem đơn bắt buộc đăng nhập, thay thế phạm vi guest checkout/OTP ban đầu. API `my-orders` lọc đúng Customer.user kể cả khi tài khoản có quyền nhân viên/Admin; `/lookup` chuyển về lịch sử cá nhân. API/adapter OTP cũ đã gỡ, giữ bảng lịch sử cũ; không tự nhận đơn guest bằng số điện thoại. POS vẫn cho phép nhân viên bán cho khách vãng lai theo quyền chi nhánh.

Hai React/Vite JavaScript app trên 5173 (khách) và 5174 (nhân viên), cùng API Django REST `/api/v1` trên 8000. Vite proxy `/api` để cookie/CSRF hoạt động cùng origin; CORS chỉ cho hai origin cụ thể. MySQL InnoDB utf8mb4, isolation READ COMMITTED, timezone nghiệp vụ Asia/Ho_Chi_Minh. Không có backend Node hoặc dịch vụ trung gian.

Custom user email chuẩn hóa lowercase, Django password hashing/session HttpOnly; CSRF cả login và request ẩn danh thay đổi dữ liệu. Group/Permission là nguồn quyền duy nhất, RoleAssignment gán group với Store. Superuser toàn chuỗi; nhân viên chỉ có quyền group của assignment trong chi nhánh tương ứng. Truy vấn list/detail/export phải lọc scope trước. Customer chỉ xem profile/order sở hữu; không ghép khách theo điện thoại.

Mỗi dòng JSON -> Product + Variant, không gộp bằng tên. Snapshot JSON giữ nguyên; namespace + source ID unique, SKU unique. Slug nội bộ có hậu tố source ID khi trùng. Brand chỉ trim/collapse whitespace; Apple và Apple Chính hãng vẫn tách biệt. Specs tách theo ` | `, `:` đầu tiên, giữ chuỗi gốc; chỉ chuẩn hóa số khi khớp toàn bộ mẫu và đơn vị rõ ràng.

Mỗi chi nhánh nguồn có kho mặc định, không bịa địa chỉ/điện thoại. Tồn bootstrap ghi StockMovement INITIAL; import lại cập nhật catalog nhưng giữ giá/tồn vận hành. Tất cả thay đổi kho qua services atomic, khóa warehouse tăng dần rồi balance tăng variant ID. Warehouse lock bảo vệ cả trường hợp balance chưa tồn tại. Điều này chủ ý tuần tự hóa giao dịch cùng kho, phù hợp quy mô đồ án và tránh race tạo balance. Không CRUD số dư.

Checkout khóa kho, lấy giá Decimal từ Variant, tạo Order/items/reservations trong một transaction. Idempotency key thuộc session hoặc user, hash payload; cùng key khác nội dung -> 409. Thời gian bảo lưu key ít nhất vòng đời đơn; không tự xóa. PENDING hết hạn hủy và giải phóng; confirmed không hết hạn theo TTL pending. POS draft không giữ; finish kiểm tra lại tồn, thu tiền, xuất kho, tạo invoice atomic.

Kho thực tế và giữ chỗ độc lập: available=on_hand-reserved. Dispatch transfer tiêu thụ reservation nguồn; hàng IN_TRANSIT tính từ transfer items, nằm ngoài hai kho. Receive toàn bộ một lần. Online ship xuất kho một lần. Payment thu/hoàn thủ công unique key, snapshot amount; invoice one-to-one không có hiệu ứng kho/tiền. Audit không chứa OTP/token/password/chat.

API chatbot trả 503 AI_NOT_CONFIGURED. Retrieval lọc catalog trong MySQL và trả dữ liệu đã kiểm chứng, không gọi Gemini. Chat chỉ ở React state. Google OpenID Connect dùng code + PKCE, MySQL state một lần buộc session, nonce và google-auth xác minh JWT. Facebook Login dùng code flow, state/session một lần và kiểm tra app/user/expiry qua debug_token trước khi lấy profile. Hai provider tạo phiên Django; email trùng cần liên kết rõ từ hồ sơ sau đăng nhập, không auto-link. Chi tiết tại docs/GOOGLE_LOGIN.md và docs/FACEBOOK_LOGIN.md.

## Ranh giới transaction và báo cáo

VNPay sandbox đã tích hợp ngày 20/10/2026: tạo request theo giá server, HMAC-SHA512, IPN kiểm tra merchant/reference/amount/transaction và khóa kho→đơn→attempt. POST check do owner gọi có CSRF/throttle sử dụng QueryDR ký trực tiếp tới provider khi thiếu IPN, dùng chung xử lý capture idempotent; không giữ khóa trong lúc gọi mạng. Return chỉ đọc. Capture tự động có actor=null; late/duplicate payment giữ để review, không hồi sinh tồn; không xác nhận tay hoặc tự hoàn tiền qua API provider. Ưu đãi VNPay đã xác minh lưu riêng trên attempt, không trừ vào grand_total lần nữa. QR/thẻ hiển thị tại cổng sandbox; không tích hợp thanh toán production. Xem docs/VNPAY_SANDBOX.md.

Atomic: import toàn file; checkout; mỗi chuyển trạng thái; post chứng từ; approve/dispatch/receive/cancel transfer; thu/hoàn; finish POS. Khóa theo kho rồi đối tượng nguồn; service khóa lại và kiểm tra trạng thái trong transaction. DB constraints là lớp bảo vệ cuối. Errors trả code/message/fields/request_id, không trả secrets/stacktrace.

Doanh thu bán = tổng grand_total đơn COMPLETED có paid_at, theo completed_at, trừ giao dịch REFUND theo ngày hoàn. Thu tiền = CAPTURE - REFUND theo created_at. Không tính lợi nhuận. Lọc ngày [đầu ngày, đầu ngày kế tiếp) theo timezone nghiệp vụ và scope; export cùng queryset, chống CSV formula injection.

## Phạm vi

Mã giảm giá cửa hàng thuộc app orders: Coupon định nghĩa điều kiện; CouponRedemption giữ/chốt/trả lượt theo vòng đời đơn. Checkout preview giá server, tạo đơn khóa tài khoản trước kho/sản phẩm/mã để kiểm tra đơn đầu và hạn mức đồng thời. Order lưu snapshot giảm giá, VNPay lấy grand_total sau giảm. Chi tiết tại docs/COUPONS.md.

PortalCookieMiddleware đứng trước SessionMiddleware/CSRF middleware, chọn cookie admin riêng bằng Host frontend hoặc Origin của API trực tiếp; ánh xạ cookie theo từng request và response, không thay đổi Django settings dùng chung. Cửa hàng giữ tên cookie hiện tại; admin dùng hậu tố `_staff`, không fallback sang phiên khách. Chặn Origin khách gọi Host admin để tránh CORS mượn cookie staff. Proxy cần giữ Host frontend; hai frontend dùng origin riêng theo cấu hình. Quyền API vẫn do owner/role checks quyết định. Đổi mật khẩu vẫn vô hiệu hóa phiên cũ theo quy tắc bảo mật Django.

Làm ngay: tài khoản/Google/Facebook Login, catalog/import, chi nhánh/kho, nhà cung cấp, nghiệp vụ kho/điều chuyển, giỏ hàng, online/POS, tiền thủ công, lịch sử và chi tiết đơn theo tài khoản, invoice, báo cáo, audit, hai UI. Deferred: Gemini và delivery email thật. Ngoài phạm vi: tự động thanh toán/đối soát, thuế/hóa đơn điện tử, loyalty, vận chuyển, đầy đủ bảo hành/đổi trả.
