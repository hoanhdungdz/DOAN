# Mã giảm giá cửa hàng

Checkout hiển thị danh sách mã và lý do chưa đủ điều kiện, cho phép chọn/nhập/bỏ một mã, cập nhật tiền giảm và tổng thanh toán từ backend. Mã của Tech Retail độc lập với ưu đãi tại VNPay.

## Dữ liệu mẫu

Sau `python manage.py migrate`, chạy `python manage.py seed_coupons` trong `be/`:

| Mã | Quy tắc |
|---|---|
| TECH100K | Giảm 100.000đ, tiền hàng từ 5.000.000đ |
| CHAO5 | Giảm 5%, tối đa 200.000đ, đơn đầu từ 1.000.000đ |
| PHUKIEN50K | Giảm 50.000đ, riêng tiền hàng thuộc danh mục `Phu_kien_Cong_nghe` từ 500.000đ |

Mỗi khách một lượt/mã; tối đa 1.000 lượt/mã; hiệu lực 30 ngày kể từ khi tạo dữ liệu mẫu. Chạy lại lệnh giữ nguyên mã đã có, không đổi thời hạn hoặc điều kiện do admin chỉnh sửa. Thiếu danh mục phụ kiện thì lệnh dừng, không biến mã phụ kiện thành mã áp dụng toàn bộ.

Admin → **Mã giảm giá** (`/coupons`) quản lý mức giảm, ngưỡng, mức tối đa, danh mục, thời hạn, số lượt và trạng thái. Chỉ quản trị viên được truy cập. Không xóa/đổi chuỗi mã; ngừng áp dụng bằng trạng thái để giữ lịch sử. Mức tối đa là bắt buộc với mã phần trăm. Các danh mục là danh sách tường minh, không suy đoán theo tên sản phẩm.

## Tính tiền và lượt sử dụng

- Preview không giữ lượt. Backend đọc giá và danh mục hiện tại, không nhận tiền giảm do trình duyệt quyết định. Giảm phần trăm tính trên tiền hàng thuộc danh mục áp dụng, làm tròn xuống nguyên VND; không giảm phí vận chuyển. Tổng sau giảm phải còn ít nhất 1đ.
- Tạo đơn khóa tài khoản khách, kho, sản phẩm và mã theo thứ tự ổn định; kiểm tra lại điều kiện và lưu snapshot. `quoted_total` chỉ dùng phát hiện thay đổi giá/ưu đãi, không dùng làm nguồn giá. Sai điều kiện hoặc tổng thay đổi sẽ rollback cả đơn, tồn giữ và lượt mã.
- Lượt `RESERVED` khi tạo đơn online. Chốt `USED` khi thu tiền hợp lệ (COD/chuyển khoản thủ công hoặc IPN VNPay). Giao dịch lặp không chốt thêm lượt.
- Hủy/hết hạn đơn chưa thanh toán trả lượt `RELEASED`. Đơn giữ lượt hết hạn không chiếm hạn mức khi kiểm tra ưu đãi. Lượt đã dùng không tự hoàn lại khi hủy/hoàn tiền. IPN về sau khi hủy/hết hạn đi vào đối soát, không khôi phục mã hay đơn.
- “Đơn đầu” nghĩa là chưa có đơn khác còn hiệu lực hoặc đã được thanh toán trong hệ thống, kể cả đơn không dùng mã. Đơn hủy/hết hạn chưa thanh toán không chặn ưu đãi. Các đơn đã thanh toán rồi hoàn tiền vẫn được tính.
- Đơn lưu `coupon_code`, `coupon_snapshot`, `discount_total`; `grand_total = subtotal - discount_total + shipping_fee`. Các dòng hàng giữ giá trước mức giảm toàn đơn. Chi tiết đơn và chứng từ tách dòng giảm giá; thay đổi mã không sửa lại đơn/chứng từ cũ.
- VNPay lấy `grand_total` đã giảm; kiểm chữ ký và so khớp tiền như trước. Có thể áp dụng thêm ưu đãi VNPay trên cổng theo điều kiện của provider. IPN/QueryDR đã xác minh lưu riêng promotion_code/promotion_amount và giao diện hiển thị số tiền sau ưu đãi VNPay; không tự trừ thêm ưu đãi VNPay vào tổng/capture của cửa hàng. Nút kiểm tra thanh toán có thể lấy lại ưu đãi thiếu trong IPN qua QueryDR.

## API

- `POST /api/v1/checkout/promotions/`: đăng nhập + CSRF; `{items: [{variant, quantity}], coupon_code?: string}` → danh sách mã, điều kiện, lỗi mã, subtotal/discount_total/grand_total và mã đã áp dụng. Không tạo đơn hay giữ lượt.
- `GET/POST /api/v1/coupons/`, `GET/PATCH/PUT /api/v1/coupons/{id}/`: chỉ admin; không DELETE.
- `POST /api/v1/orders/`: thêm `coupon_code` (online) và `quoted_total` (tùy chọn, chỉ đối chiếu).

## Kiểm tra

`tests.test_coupons` kiểm tra giá server, phần trăm/cap/danh mục, snapshot, idempotency, hạn mức, đơn đầu, hủy/hết hạn/thu/hoàn, rollback, phân quyền/CSRF, tiền VNPay sau giảm và tranh chấp đồng thời giữa hai kho/khách hoặc hai đơn đầu của cùng khách.

UI kiểm tra chọn/nhập/bỏ mã, mã không hợp lệ chặn đặt hàng, gửi tổng đã xác nhận và bỏ phản hồi preview cũ khi đổi giỏ hàng.
