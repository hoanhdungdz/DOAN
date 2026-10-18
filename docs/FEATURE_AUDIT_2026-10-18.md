# Rà soát chức năng ngày 18/10/2026

Phạm vi: đọc models, services, API routes, routes React, cấu hình màn hình Admin, tài liệu và toàn bộ JSON nguồn. Đây là rà soát code/dataset; không chạy lại bộ kiểm thử hay xác minh các dịch vụ ngoài trong lần này. Không thay đổi mã nghiệp vụ hoặc dữ liệu ứng dụng.

## Các phần đã có trong code

- Email/password, session/CSRF, đăng ký, profile, đổi/quên/reset mật khẩu; RBAC và phạm vi chi nhánh.
- Catalog, tìm/lọc, chi tiết, ảnh, specs, giá/tình trạng/số tháng bảo hành; Admin quản lý metadata và import/review nguồn.
- Chi nhánh, kho, nhà cung cấp, số dư/giữ chỗ/lịch sử kho, chứng từ và điều chuyển.
- Giỏ guest/customer, checkout, đơn online, POS, trạng thái đơn, hết hạn giữ hàng, tra cứu OTP.
- Thu/hoàn tiền thủ công, COD, chuyển khoản nhân viên xác nhận, invoice nội bộ, báo cáo/CSV và audit.

Có code và luồng xử lý không có nghĩa mọi màn hình đã UAT hoặc dịch vụ ngoài đã hoạt động; xem TEST_RESULTS.md và DEFERRED_INTEGRATIONS.md.

## Bảo hành: có dữ liệu thời hạn, chưa có module/chính sách

ProductVariant.warranty_months lưu số tháng, được import và Admin sửa; trang chi tiết hiển thị “Bảo hành N tháng”. Không có trang chính sách bảo hành trong routes/footer, entity/API chính sách, coverage/claim/RMA, tiếp nhận/sửa chữa/trả máy, serial/IMEI hoặc tra cứu hạn bảo hành. “Đổi bảo hành” trong bộ lọc chỉ là nhãn tình trạng của sản phẩm.

OrderItem hiện snapshot tên, SKU, giá, condition/attributes, nhưng không có trường hoặc logic bảo đảm snapshot warranty_months/policy version lúc bán. Nếu làm bảo hành sau bán, cần lưu quyền lợi tại thời điểm mua và quy định mốc bắt đầu; không chỉ đọc warranty_months hiện tại vì Admin có thể đổi nó sau khi đã bán.

Chưa có trang chính sách đổi trả, giao hàng/thanh toán hay bảo mật riêng trong storefront. Hủy đơn/hoàn tiền trước xuất đang có không tương đương module đổi trả sau giao hàng.

## Mã giảm giá: chưa triển khai

Không có Coupon/Voucher/Promotion model, API quản lý/áp dụng, màn hình Admin hoặc ô nhập mã checkout. OrderItem.discount có default0, nhưng create_order đang tính line_total = price × quantity, grand_total = tổng line_total. Trường dự phòng này chưa tạo ra chức năng giảm giá.

Để triển khai cần quy tắc do cửa hàng quyết định: giảm tiền/% và mức trần, đơn tối thiểu, thời gian hiệu lực, phạm vi hàng/chi nhánh/kênh, giới hạn toàn chương trình/mỗi khách, cộng dồn và trả lượt khi đơn hủy. Backend phải tính/kiểm tra lại khi đặt đơn, lưu snapshot và chống vượt số lượt khi nhiều người đặt đồng thời.

## Các phần đã trao đổi nhưng chưa được thêm vào code

- QR/VNPAY/MoMo sandbox: payment methods hiện chỉ COD/CASH/BANK_TRANSFER; không có gateway callback/IPN.
- Tự chọn kho gần địa chỉ nhận: Store chưa có latitude/longitude; checkout còn chọn kho thủ công, chưa có geocoding/ranking service.
- Google/Facebook login và Gemini: flags/interface disabled, không là tích hợp hoạt động.
- Email/SMS thật: mới có delivery development, cần adapter/cấu hình và kiểm thử nhà cung cấp.
- Chưa có chức năng đánh giá/xếp hạng, yêu thích/so sánh sản phẩm, tích điểm hoặc tính phí/kết nối đơn vị vận chuyển trong routes/models hiện tại.

## Có cần crawl thêm dữ liệu?

Chưa cần crawl thêm để làm chính sách bảo hành hoặc mã giảm giá. Đây chủ yếu là thiếu nội dung/quy tắc riêng và chức năng ứng dụng. Mã giảm giá của cửa hàng khác không có hiệu lực cho hệ thống này; chính sách của cửa hàng khác cũng không tự trở thành cam kết của Tech Retail.

JSON hiện có278 dòng,16 trường; mọi dòng có warranty_months: 86 dòng6 tháng,134 dòng12 tháng,1 dòng18 tháng,57 dòng24 tháng. Không có trường policy/coupon/voucher/promotion/discount. Có202 mô tả nhắc bảo hành và199 mô tả nhắc ưu đãi/trả góp/đổi mới; đây là text quảng cáo, không phải policy/promotion có thể thực thi.

Ví dụ PROD_0001 và PROD_0002 có warranty_months=24 nhưng description ghi “bảo hành 6-12 tháng”. Chưa kết luận giá trị nào đúng; phải xác minh theo mẫu hàng/tình trạng/đơn vị bảo hành trước khi dùng làm cam kết. Không tự sửa hàng loạt thành12 hoặc24 tháng từ câu quảng cáo.

Nên ưu tiên chuẩn hóa dữ liệu đang có: đối soát thời hạn bảo hành, mô tả/mẫu/cấu hình, ảnh đúng sản phẩm, và địa chỉ/tọa độ cơ sở do chủ cửa hàng xác nhận. Chỉ thu thập bổ sung có chọn lọc khi thiếu thông số, ảnh phụ hoặc thông tin bảo hành từ nguồn xác minh được; lưu nguồn/thời điểm và tách dữ liệu tham khảo khỏi chính sách cửa hàng. Không import thêm tồn/giá/chương trình ưu đãi của website khác như dữ liệu vận hành thực tế.

Thứ tự đề xuất: hoàn thiện các trang chính sách và dữ liệu bảo hành → mã giảm giá có nghiệp vụ backend → chọn cơ sở theo địa chỉ/QR sandbox nếu mở rộng phạm vi → module bảo hành/đổi trả sau bán theo yêu cầu đồ án. Tính năng đánh giá/yêu thích/so sánh tùy mục tiêu giao diện, không bắt buộc để hoàn thiện hai phần đang hỏi.

## Điểm đối chiếu trong source

- be/apps/products/models.py: ProductVariant.warranty_months.
- admin/src/features/resources/config.js: form và cột số tháng bảo hành.
- fe/src/pages/ProductDetail.jsx: hiển thị thời hạn bảo hành.
- be/apps/orders/models.py: OrderItem.discount và các trường snapshot.
- be/apps/orders/services.py: create_order tính tiền không áp dụng voucher; invoice snapshot.
- be/config/urls.py, fe/src/main.jsx, fe/src/layouts/CustomerLayout.jsx: không có route/API/link chính sách, voucher hoặc bảo hành sau bán.
- be/data/final_master_dataset.json:16 trường nguồn và các mô tả mâu thuẫn nói trên.
