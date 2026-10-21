# Kế hoạch kiểm thử

Chạy trên MySQL riêng cho project, không SQLite. Unit validation và API integration dùng Django test runner; concurrency dùng TransactionTestCase và hai kết nối MySQL thật. CSDL test do Django tạo với prefix test_, không tác động dữ liệu ứng dụng.

Nhóm: toàn dataset/dry-run/idempotency/conflict/rollback; session và CSRF kể cả anonymous; register không nâng quyền; disabled/locked account; reset token hết hạn/một lần; customer ownership; branch list/detail/mutation/export; cart/merge; checkout giá server và payload mismatch; reservation hết hạn/hủy/xuất một lần; last unit race; stock draft/post và immutable; transfer approve/dispatch/receive/cancel; payment idempotency/refund; POS atomic; đăng nhập bắt buộc khi checkout/xem đơn; my-orders chỉ sở hữu kể cả Admin/nhân viên; không ghép đơn guest theo điện thoại; API OTP cũ 404; đổi tài khoản không giữ nội dung riêng tư; quay lại trang đơn sau login; invoice không có side effect; report timezone/scope/refund; retrieval và AI disabled; hai Vite production builds và browser smoke.

Chỉ ghi PASS sau khi đã chạy; phân biệt test fixture với dữ liệu nguồn. Kết quả, command và giới hạn được cập nhật trong TEST_RESULTS.md.

Google Login: kiểm tra JWT ký RSA qua google-auth, sai chữ ký/aud/iss/exp/nonce/email_verified/azp; state dùng một lần buộc session/host và hết hạn; hủy/network error; không tự liên kết email; liên kết rõ không đổi User/Customer và không chiếm SocialIdentity; tài khoản khóa; trả về đơn/checkout, gộp giỏ hoặc khôi phục khi lỗi. Browser kiểm tra nút và mở trang Google thật; hoàn tất cấp quyền tài khoản thật là bước UAT của người dùng.
