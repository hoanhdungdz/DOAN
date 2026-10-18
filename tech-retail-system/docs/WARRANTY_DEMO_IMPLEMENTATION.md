# Chính sách bảo hành trong phiên bản đồ án

Phiên bản TR-BH-2026.01, hiệu lực mô phỏng từ 18/10/2026. Các quy định do người dùng cho phép tạo cho đồ án; không dùng làm tài liệu xác nhận quyền lợi của hãng hoặc CellphoneS.

## Giao diện đã triển khai

Trong thông tin sản phẩm, bên dưới tình trạng có khung xám bo góc, biểu tượng khiên đỏ và nút chữ xanh “Xem chi tiết”. Số tháng được đọc từ `warranty_months` của biến thể đang chọn. Mỗi lần chọn biến thể khác, thông tin được cập nhật; hộp chi tiết cũ đóng khi đổi sang biến thể khác.

- Mới 100%: “Bảo hành N tháng chính hãng.”
- Hàng cũ, đã kích hoạt, đổi bảo hành và tình trạng khác: “Bảo hành N tháng tại Tech Retail.”
- Giá trị 0: ghi không áp dụng bảo hành, không tự thêm thời hạn.
- Thiếu thời hạn: ghi chưa có thời hạn, không mặc định 12 tháng.

Nút mở hộp chi tiết có tên sản phẩm, SKU, tình trạng và số tháng hiện tại. Hỗ trợ đóng bằng nút X, Escape hoặc bấm nền ngoài; giữ tiêu đề và nút đóng khi cuộn nội dung; khóa cuộn trang nền và khôi phục khi đóng/chuyển trang. Dùng dialog gốc của trình duyệt để quản lý focus và ngăn tương tác với trang nền.

## Quy tắc mô phỏng

1. Thời hạn thân máy theo dữ liệu biến thể, tính từ ngày giao/nhận tại quầy. Hàng mới được mô phỏng bảo hành hãng đủ số tháng; với hàng đã kích hoạt/cũ/đổi bảo hành, Tech Retail đảm nhiệm đủ số tháng đã hiển thị.
2. Pin tích hợp nếu có: tối đa 12 tháng với hàng mới, 6 tháng với tình trạng khác; phụ kiện trong bộ bán tối đa 6 tháng. Các thời hạn này không vượt thời hạn thân máy. Không hiển thị mục pin cho Mac mini, màn hình PC hoặc tivi. Phụ kiện bán riêng theo thời hạn của chính sản phẩm đó.
3. Phạm vi chia theo 8 nhóm catalog. Màn hình PC có tiêu chí mô phỏng từ 3 điểm sáng hoặc 5 điểm tối để đánh giá thay tấm nền. Tivi hỗ trợ kiểm tra tại nhà trong bán kính mô phỏng 15 km. Phân biệt vật tư tiêu hao theo nhóm hàng.
4. Đổi lỗi phần cứng thuộc phạm vi bảo hành trong 30 ngày, cùng mẫu/cấu hình/tình trạng tương đương. Nếu hết hàng, thỏa thuận chờ, đổi mẫu và chênh lệch hoặc hoàn số tiền thực trả cho sản phẩm. Sau 30 ngày ưu tiên sửa/thay linh kiện. Không áp dụng đổi vì thay đổi nhu cầu khi máy không lỗi.
5. Đối chiếu đơn hàng hoặc chứng từ, ghi ngoại hình, phụ kiện và serial/IMEI nếu có. Phân biệt lỗi đang yêu cầu xử lý với khuyết điểm cũ. Sửa có phí cần báo giá và khách đồng ý. Sao lưu dữ liệu; không yêu cầu mật khẩu tài khoản.
6. Phản hồi trong 1 ngày làm việc; dự kiến sửa 3–7 ngày làm việc, mốc xử lý 15 ngày. Nếu kéo dài phải thông báo và thống nhất. Linh kiện thay thế được bảo hành theo thời hạn còn lại hoặc 3 tháng, chọn thời gian dài hơn; máy đổi tiếp tục hạn ban đầu.
7. Miễn phí vận chuyển hai chiều với lỗi được bảo hành; ngoài phạm vi báo phí thực tế trước. Ba quầy mô phỏng theo các cơ sở có trong dự án: Cầu Giấy — Hà Nội, Thanh Xuân — Hà Nội, Hoàng Diệu — Hải Phòng; 08:30–20:00 hằng ngày. Không tạo số điện thoại hoặc địa chỉ nhà có thể bị hiểu là cơ sở thật.
8. Chưa có gói bảo hành mở rộng có phí. Các phiếu, serial/IMEI và công việc sửa chữa mô tả quy trình demo; chưa bổ sung model/API quản lý dịch vụ sau bán trong phạm vi giao diện này.

## Nhất quán dữ liệu

Mô tả quảng cáo có thời hạn dạng số tháng được chuẩn hóa khi hiển thị để theo biến thể, ví dụ 6–12 tháng thành 24 tháng nếu `warranty_months=24`. Không sửa bản JSON nguồn hoặc database. Bảng [đối chiếu 264 dòng](WARRANTY_PRODUCT_REFERENCE.md) giữ vai trò truy vết nguồn; không tự hạ toàn bộ laptop xuống 12 tháng hoặc gộp các SKU.

## Mã nguồn và kiểm tra

- `shared/warranty.js`: phiên bản, quầy dịch vụ, thời gian xử lý, phân nhóm phạm vi và tính thời hạn.
- `fe/src/components/ProductWarranty.jsx`: ô tóm tắt và dialog theo sản phẩm.
- `fe/src/pages/ProductDetail.jsx`: tích hợp biến thể hiện tại và chuẩn hóa mô tả hiển thị.
- `fe/src/styles.css`: giao diện và khả năng cuộn trên màn hình nhỏ.
- `shared/ProductWarranty.test.jsx`: kiểm tra thời hạn thay đổi, nhóm hàng, đóng dialog, khôi phục cuộn và mâu thuẫn thời hạn trong mô tả.

Tài liệu này thay thế các đề xuất chưa chốt trong bản nghiên cứu ban đầu cho phiên bản demo hiện tại.

## Kết quả kiểm tra

- `npm run test:ui`: 4 kiểm tra Node và 11 kiểm tra Vitest đều đạt, gồm 4 kiểm tra mới cho bảo hành.
- `npm run build -w fe`: đạt.
- Đối chiếu API local: đủ 264 biến thể đang hoạt động trong 8 nhóm; số tháng tính cho giao diện khớp trường của từng biến thể.
- Trình duyệt: kiểm tra hàng cũ 6 tháng ở khung 320px, Mac mini mới 12 tháng và laptop mới 24 tháng ở khung 1440px; nội dung chính sách mở được. Mac mini không hiển thị mục pin. Đóng bằng X/Escape khôi phục cuộn trang và đưa focus về nút chi tiết.
- Ảnh kết quả: `docs/screenshots/product-warranty-card.png`.
