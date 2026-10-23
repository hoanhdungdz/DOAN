# Đặt hàng, thanh toán và mã giảm giá TechRetail

Đặt hàng online và xem đơn yêu cầu đăng nhập tài khoản TechRetail. Trang Đơn hàng của tôi chỉ hiển thị đơn thuộc tài khoản hiện tại. Chatbot không tra cứu dữ liệu đơn riêng tư; khách mở mục Đơn hàng của tôi để xem trạng thái.

Giá bán, biến thể và tồn kho khả dụng được backend kiểm tra khi đặt hàng. Số tồn và giá có thể thay đổi sau lúc tư vấn; việc chatbot đề xuất sản phẩm không đồng nghĩa giữ hàng hoặc đặt hàng thành công. Chi nhánh đủ hàng được lựa chọn ở bước checkout theo dữ liệu hệ thống.

Thanh toán qua VNPay hiện dùng môi trường thử nghiệm, tài khoản hoặc thẻ test. Trạng thái đã thanh toán chỉ cập nhật sau xác minh của backend. Không quét QR thử nghiệm bằng ứng dụng ngân hàng thật để chuyển tiền thật. Khi có lỗi, khách xem kết quả thanh toán hoặc chi tiết đơn hàng.

Mã giảm giá TechRetail được kiểm tra ở checkout theo thời gian, giá trị đơn, danh mục, số lượt và điều kiện tài khoản. Không tự tạo hoặc cam kết mã còn dùng được khi chưa kiểm tra. Ưu đãi trên VNPay có điều kiện riêng do VNPay quyết định. Có thể kết hợp ưu đãi cửa hàng và ưu đãi VNPay nếu cả hai đáp ứng điều kiện; khoản giảm của VNPay chỉ được hiển thị sau khi backend xác minh giao dịch. Chatbot không xác nhận trước số tiền giảm.

Chưa có nguồn chính sách đầy đủ về trả góp, đặt trước hoặc cước giao hàng cho từng địa chỉ. Khi khách hỏi các nội dung này, nói rõ chưa có thông tin xác nhận, không tự đặt mức lãi suất, hạn mức, phí hoặc thời gian giao hàng.
