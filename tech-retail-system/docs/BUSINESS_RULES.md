# Quy tắc nghiệp vụ và trạng thái

| Nguồn | Action | Đích | Điều kiện/hiệu ứng |
|---|---|---|---|
| Online mới | checkout | PENDING | Đã đăng nhập; customer gắn tài khoản; đủ khả dụng toàn đơn; giữ chỗ; snapshot giá backend |
| PENDING | confirm | CONFIRMED | Chưa hết TTL; nhân viên bán hàng/manager đúng chi nhánh |
| CONFIRMED | pack | PACKING | Nhân viên xử lý đúng scope |
| PACKING | ship | SHIPPED | Giảm on_hand và reserved; movement SALE một lần |
| SHIPPED | complete | COMPLETED | Đã thu tiền và giao/nhận được xác nhận bởi action |
| PENDING | cancel/expire | CANCELLED | Chủ đơn hoặc nhân viên; giải phóng reservation |
| CONFIRMED/PACKING | cancel | CANCELLED | Nhân viên có quyền; giải phóng; paid -> REFUND_PENDING |
| POS DRAFT | finish | COMPLETED | CASH/BANK_TRANSFER; thu tiền, xuất và invoice atomic |
| POS DRAFT | cancel | CANCELLED | Không có giữ chỗ |

Không hủy SHIPPED/COMPLETED. Không sửa status bằng PATCH. Không cho khách tự đặt PAID. PENDING hết hạn được kiểm tra khi action và bằng `expire_reservations`; chạy command mỗi phút bằng Task Scheduler/cron. Chưa có worker tự động.

| Đối tượng | Chuyển trạng thái | Hiệu ứng |
|---|---|---|
| Payment | UNPAID -> PAID | Nhân viên CAPTURE đúng tổng; BANK_TRANSFER bắt buộc reference |
| Payment | PAID -> REFUND_PENDING | Đơn hủy trước xuất; tiền chưa tự hoàn |
| Payment | REFUND_PENDING -> REFUNDED | Nhân viên REFUND thủ công, tham chiếu bắt buộc |
| StockDocument | DRAFT -> POSTED | IN/OUT/ADJUST delta; phải có reason; ghi một lần |
| StockDocument | DRAFT -> CANCELLED | Không tác động kho |
| Transfer | DRAFT -> APPROVED | Giữ kho nguồn |
| Transfer | APPROVED -> IN_TRANSIT | Xuất nguồn; tiêu thụ giữ chỗ |
| Transfer | IN_TRANSIT -> RECEIVED | Nhập đủ đích một lần |
| Transfer | DRAFT/APPROVED -> CANCELLED | Giải phóng giữ nếu có |
| Reservation | ACTIVE -> CONSUMED | Xuất kho; lưu history |
| Reservation | ACTIVE -> RELEASED | Hủy/hết hạn; không cộng on_hand |

Guest cart localStorage chỉ variant ID/quantity; customer cart backend. Merge cộng quantity rồi validate variant active và hạn mức, báo không đủ tồn khi checkout; giỏ không giữ kho. Shipping fee 0, không giảm giá mặc định. Không tự liên kết Customer theo số điện thoại. Chứng từ POSTED bất biến; sai sót lập chứng từ điều chỉnh có reason.

Mã giảm giá cửa hàng: một mã/đơn online; mức giảm tính lại trên backend, lưu snapshot trên đơn. Giữ lượt khi đặt hàng, chốt khi thu tiền, trả lượt cho đơn chưa thanh toán hủy/hết hạn; lượt đã dùng không tự trả sau hoàn tiền. Khóa tài khoản/mã để bảo vệ điều kiện đơn đầu và hạn mức đồng thời. VNPay thu theo tổng sau giảm; ưu đãi của VNPay tách riêng. Chi tiết tại `COUPONS.md`.

Theo yêu cầu cập nhật ngày 19/10/2026, không dùng OTP để tra cứu đơn. Chưa đăng nhập khi vào checkout/lịch sử/chi tiết thì chuyển đến login và quay lại sau khi đăng nhập. Trang Đơn hàng của tôi dùng `my-orders`, chỉ trả các đơn có customer.user trùng phiên, không kế thừa quyền chi nhánh/Admin. Đơn khách vãng lai cũ không tự gắn tài khoản theo điện thoại; bảng OTPChallenge chỉ giữ lịch sử, không có API tạo/xác minh/cấp grant.

## Ma trận quyền

| Vai trò | Catalog/tài khoản | Đơn/POS/thanh toán | Kho/điều chuyển | Báo cáo |
|---|---|---|---|---|
| Admin | Toàn chuỗi | Toàn chuỗi | Toàn chuỗi | Toàn chuỗi |
| Store Manager | Hồ sơ nhân viên trong scope; không gán quyền | Chi nhánh được giao | Chi nhánh được giao | Chi nhánh được giao |
| Sales Staff | Đọc catalog/khách trong scope | Chi nhánh được giao | Đọc tồn trong scope | Không mặc định |
| Warehouse Staff | Đọc catalog | Không truy cập PII đơn | Chi nhánh được giao; nguồn xuất, đích nhận | Tồn trong scope |
| Customer | Profile chính mình | Đơn chính mình; hủy PENDING | Chỉ tồn công khai | Không |
| Guest | Catalog, giỏ local | Phải đăng nhập để đặt/xem đơn | Chỉ tồn công khai | Không |

Nhiều assignment: hợp quyền trong từng chi nhánh; quyền ở A không áp dụng ở B. Gán role/permission và khóa tài khoản chỉ Admin. Manager được sửa thông tin Employee trong scope, không thay user/assignment.
