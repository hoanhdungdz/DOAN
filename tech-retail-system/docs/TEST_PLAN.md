# Kế hoạch kiểm thử

Chạy trên MySQL riêng cho project, không SQLite. Unit validation và API integration dùng Django test runner; concurrency dùng TransactionTestCase và hai kết nối MySQL thật. CSDL test do Django tạo với prefix test_, không tác động dữ liệu ứng dụng.

Nhóm: toàn dataset/dry-run/idempotency/conflict/rollback; session và CSRF kể cả anonymous; register không nâng quyền; disabled/locked account; reset token hết hạn/một lần; customer ownership; branch list/detail/mutation/export; cart/merge; checkout giá server và payload mismatch; reservation hết hạn/hủy/xuất một lần; last unit race; stock draft/post và immutable; transfer approve/dispatch/receive/cancel; payment idempotency/refund; POS atomic; OTP sai/hết hạn/reuse/cooldown/grant đúng order; invoice không có side effect; report timezone/scope/refund; retrieval và AI disabled; hai Vite production builds và browser smoke.

Chỉ ghi PASS sau khi đã chạy; phân biệt test fixture với dữ liệu nguồn. Kết quả, command và giới hạn được cập nhật trong TEST_RESULTS.md.
