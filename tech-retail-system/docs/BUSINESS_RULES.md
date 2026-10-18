# Quy tắc nghiệp vụ và trạng thái

| Nguồn | Action | Đích | Điều kiện/hiệu ứng |
|---|---|---|---|
| Online mới | checkout | PENDING | Đủ khả dụng toàn đơn; giữ chỗ; snapshot giá backend |
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
| OTP | CREATED -> VERIFIED | Hash kiểm chứng, 5 phút, một lần; cấp grant đúng một order 10 phút |
| OTP | CREATED -> EXPIRED/LOCKED | Hết hạn/5 lần sai; gửi lại tối thiểu 60 giây |

Guest cart localStorage chỉ variant ID/quantity; customer cart backend. Merge cộng quantity rồi validate variant active và hạn mức, báo không đủ tồn khi checkout; giỏ không giữ kho. Shipping fee 0, không giảm giá mặc định. Không tự liên kết Customer theo số điện thoại. Chứng từ POSTED bất biến; sai sót lập chứng từ điều chỉnh có reason.

## Ma trận quyền

| Vai trò | Catalog/tài khoản | Đơn/POS/thanh toán | Kho/điều chuyển | Báo cáo |
|---|---|---|---|---|
| Admin | Toàn chuỗi | Toàn chuỗi | Toàn chuỗi | Toàn chuỗi |
| Store Manager | Hồ sơ nhân viên trong scope; không gán quyền | Chi nhánh được giao | Chi nhánh được giao | Chi nhánh được giao |
| Sales Staff | Đọc catalog/khách trong scope | Chi nhánh được giao | Đọc tồn trong scope | Không mặc định |
| Warehouse Staff | Đọc catalog | Không truy cập PII đơn | Chi nhánh được giao; nguồn xuất, đích nhận | Tồn trong scope |
| Customer | Profile chính mình | Đơn chính mình; hủy PENDING | Chỉ tồn công khai | Không |
| Guest | Catalog | Checkout và OTP grant một đơn | Chỉ tồn công khai | Không |

Nhiều assignment: hợp quyền trong từng chi nhánh; quyền ở A không áp dụng ở B. Gán role/permission và khóa tài khoản chỉ Admin. Manager được sửa thông tin Employee trong scope, không thay user/assignment.
