# Nhập thêm hàng và chọn chi nhánh checkout — 19/10/2026

Đối chiếu SKU-DIE-0052 trong database ứng dụng: Cầu Giấy còn 3, Hoàng Diệu và Thanh Xuân đều 0. Ba dòng Tồn kho là ba kho chi nhánh. Checkout trước đây vẫn cho chọn kho hết hàng, chỉ báo lỗi chung khi gửi đơn.

- Bảng Tồn kho có tên chi nhánh và tên kho thay ID; bộ lọc chi nhánh là danh sách lựa chọn theo tài khoản.
- Người có manage_stock thấy Nhập thêm hàng tại Sản phẩm, Biến thể & giá, Tồn kho. Chọn biến thể/kho, nhập số lượng bổ sung nguyên dương và lý do rồi Xác nhận nhập kho. Dùng API StockDocument IN hiện có, tạo nháp rồi ghi sổ; lưu movement/audit, không sửa balance trực tiếp. Từ dòng tồn kho sẽ điền sẵn đúng kho và SKU.
- Nếu phản hồi ghi sổ bị mất/lỗi, dialog giữ ID phiếu và khóa dữ liệu; thử lại cùng phiếu, không cộng tồn hai lần. Nếu đóng khi có nháp thì vào Chứng từ kho kiểm tra trước khi tạo phiếu khác. Backend kiểm tra quyền theo chi nhánh.
- Checkout chọn sẵn kho đủ toàn bộ giỏ khi chưa có lựa chọn, hiện lượng còn tại kho trên mỗi dòng, vô hiệu kho thiếu/hết hàng và nút đặt hàng khi không đủ. Không cộng dồn tồn nhiều kho cho một đơn. Khi lượng mua thay đổi không tự đổi chi nhánh đã chọn; hướng dẫn chọn nơi khác hoặc giảm/tách giỏ.
- Kiểm tra lại khi quay về tab; server trả INSUFFICIENT_STOCK thì tải tồn mới, giữ giỏ và không tự gửi lại đơn. Đã bỏ khung thông báo đủ hàng, nút kiểm tra thủ công và ghi chú chưa có cổng thanh toán theo yêu cầu giao diện. Thông báo thiếu hàng vẫn được giữ. Giá/tồn chính thức vẫn được kiểm tra trong transaction có khóa ở backend.
- POST `carts/availability/` yêu cầu đăng nhập/CSRF, trả snapshot công khai của biến thể đang bán cho giỏ gửi lên, không sửa giỏ/đặt đơn mới. Trước snapshot, giải phóng PENDING hết hạn trong kho active liên quan bằng expire_orders; không đụng giữ chỗ chưa hết hạn. Dùng POST vì có thể chuyển trạng thái hết hạn. Chạy expire_reservations định kỳ vẫn cần cho các đơn không có người quay lại checkout.

Browser kiểm tra fixture riêng trong `test_tech_retail`, cổng 8001/5175/5176 và cookie riêng: bảng hiện Cầu Giấy 3/Hoàng Diệu 0/Thanh Xuân 0; từ Sản phẩm tạo/ghi sổ IN +5 vào Hoàng Diệu; checkout cập nhật đủ hàng và đặt đơn thành công. Đối chiếu on_hand=5, reserved=1, available=4; 834 số dư/ledger không sai lệch. Đã dừng server và dọn fixture. Database ứng dụng giữ nguyên 3/0/0, không tạo phiếu nhập hoặc đơn thử ở đó.

Ảnh tại `.runtime/stock-inventory-fixed.png`, `stock-receipt-dialog.png`, `stock-checkout-fixed.png`, `stock-checkout-success-test.png`. Kết quả suite mới nhất tại TEST_RESULTS.md.
