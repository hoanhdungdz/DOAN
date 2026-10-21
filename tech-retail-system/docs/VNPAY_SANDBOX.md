# VNPay sandbox — 20/10/2026

Đã tích hợp cổng thử nghiệm thật của VNPay 2.1.0. Đây là môi trường sandbox, không phải thanh toán ngân hàng thật. Mã QR do VNPay cung cấp trên cổng thanh toán, không phải ảnh QR giả trong ứng dụng.

## Cách dùng

1. Đăng nhập tại `http://localhost:5173`, tạo đơn mới và chọn **VNPay (QR / thẻ ngân hàng)**.
2. Mở chi tiết đơn → **Thanh toán ngay**. Website kiểm tra quyền sở hữu và trạng thái đơn, tạo hoặc dùng lại yêu cầu còn hiệu lực, rồi chuyển cùng tab đến VNPay; không cần bấm thêm nút mở cổng.
3. Trên VNPay chọn **App Ngân hàng và Ví điện tử (VNPay-QR)** để hiển thị QR, hoặc phương thức thẻ thử do VNPay cung cấp. Không dùng tài khoản/ngân hàng thật.
4. Sau khi VNPay chuyển về website, trang kết quả tự đọc trạng thái và tra cứu QueryDR qua backend nếu giao dịch còn chờ. Trang tự hiển thị thành công, chưa thành công hoặc cần đối soát theo kết quả đã xác minh; không cần bấm **Kiểm tra kết quả thanh toán**. Nếu chưa nhận được kết quả sau khoảng một phút, trang cho thử xác nhận lại, không tự tạo thanh toán khác hoặc coi lỗi mạng là thanh toán thất bại. Nút kiểm tra ở chi tiết đơn vẫn là phương án phục hồi riêng. Không đánh dấu đã thanh toán chỉ vì người dùng quay về trang kết quả.

Mỗi đơn dùng một mã cửa hàng ở checkout. Có thể dùng thêm ưu đãi của VNPay trên cổng nếu đáp ứng điều kiện của chương trình đó. Ví dụ: tiền hàng 16.390.000đ, TECH100K giảm 100.000đ → tổng đơn gửi VNPay 16.290.000đ; VNPay xác nhận ưu đãi CTT0604 thêm 100.000đ → sau ưu đãi VNPay còn 16.190.000đ. Đây là hai khoản riêng: không nhập mã VNPay vào ô mã cửa hàng và không trừ lại khoản của VNPay vào Order.grand_total/PaymentTransaction.

Thông tin ưu đãi VNPay chỉ hiển thị sau IPN/QueryDR đã xác minh; không suy đoán từ nội dung trang quay về. Các trường promotion_code, promotion_amount và customer_amount phản ánh dữ liệu đã kiểm tra chữ ký của provider.

Phiên admin và khách đã được tách: cổng 5174 dùng sessionid_staff/csrftoken_staff; cổng 5173 giữ sessionid/csrftoken (tên lấy theo cấu hình cookie gốc). Có thể dùng hai tài khoản cùng một trình duyệt; nút Mở cửa hàng không chuyển phiên admin sang cửa hàng. Khi cập nhật từ bản cũ, đăng nhập lại admin một lần để tạo cookie riêng. App vẫn kiểm tra lại phiên khi quay lại tab để nhận biết đăng nhập/đăng xuất ở tab khác của cùng giao diện; 403/404 thanh toán dừng polling và bỏ URL cũ.

Luồng chọn phương thức chung đã mở được QR trên merchant cấu hình hiện tại. Gửi trực tiếp `vnp_BankCode=VNPAYQR` trả lỗi 76 từ cổng, nên giao diện mặc định không truyền bank code và cho chọn QR trên VNPay. Backend vẫn hỗ trợ lựa chọn trực tiếp khi merchant/provider hỗ trợ.

Đơn COD/chuyển khoản cũ giữ nguyên phương thức, không tự chuyển sang VNPay. Các đơn VNPay không được bấm thu/hoàn thủ công trong trang nhân viên. Việc hoàn tiền qua API VNPay chưa triển khai; giao dịch cần hoàn được ghi rõ để đối soát riêng.

## Cấu hình riêng trên máy

`be/.env` không commit:

```dotenv
VNPAY_SANDBOX_ENABLED=true
VNPAY_TMN_CODE=<mã merchant sandbox>
VNPAY_HASH_SECRET=<khóa sandbox>
VNPAY_RETURN_URL=http://localhost:5173/api/v1/payments/vnpay/return/
```

Backend chỉ dùng endpoint `https://sandbox.vnpayment.vn/paymentv2/vpcpay.html`; từ chối bật sandbox trong APP_ENV=production. Chạy migration từ be: `../.venv/Scripts/python.exe manage.py migrate`, khởi động lại backend. /features/ trả vnpay_sandbox theo cấu hình hợp lệ.

Return URL hiện dùng localhost để người dùng trên máy phát triển trở về cùng phiên đăng nhập. Khi thanh toán từ máy/điện thoại khác, localhost trên thiết bị đó không trỏ về máy phát triển; cần triển khai frontend/return HTTPS tương ứng, đồng nhất CUSTOMER_FRONTEND_URL, trusted origins và cookie. QR sandbox không đồng nghĩa có thể quét bằng mọi ứng dụng ngân hàng thật.

## Bắt buộc khai báo IPN với VNPay

VNPay phải gọi được endpoint HTTPS công khai này (link tunnel hiện tại):

```text
https://gallery-bras-recently-lender.trycloudflare.com/api/v1/payments/vnpay/ipn/
```

Khai báo URL này cho merchant theo hướng dẫn VNPay; nếu trang quản trị không cho sửa, gửi URL qua kênh hỗ trợ tích hợp VNPay. Return URL không thay thế IPN. Không chỉ đăng ký URL trang chủ rồi coi như đã cấu hình IPN.

Tunnel do người dùng tự khởi chạy, chuyển tiếp cổng 5173 với Host localhost:5173. Giữ website/backend/tunnel hoạt động khi thử. Link Quick Tunnel đổi khi tạo lại; cần cập nhật IPN tương ứng. Chỉ expose tạm phục vụ thử nghiệm; không sử dụng Vite/Django development server làm hosting production. QueryDR là cách phục hồi xác nhận thiếu, không thay thế cấu hình IPN cho luồng tự động.

## Kiểm tra phía backend

- POST tạo yêu cầu chỉ chủ đơn đã đăng nhập, có CSRF và throttle 10/phút. Số tiền lấy từ database, không nhận số tiền/tỷ giá từ client. Nhân số tiền VND với 100, ký HMAC-SHA512 trên tham số sắp xếp/urlencode, múi giờ VN. Mỗi reference UUID32, hạn tối đa 15 phút và không vượt hạn giữ hàng của đơn.
- Retry cùng phương thức khi yêu cầu còn hiệu lực trả cùng reference. Đổi phương thức rõ ràng có thể tạo reference khác; mỗi giao dịch thành công được giữ để đối soát, không bỏ qua khoản thu trùng.
- GET IPN không dùng session/CSRF của trình duyệt; bắt buộc xác minh chữ ký, merchant, reference, số tiền snapshot/đơn, mã phản hồi/trạng thái, transaction number và pay date. Từ chối query lặp trường. Return chỉ kiểm tra và hiển thị, không cập nhật tiền.
- Khóa theo thứ tự warehouse → order → attempt, cùng quy ước với kho/hủy/hết hạn. IPN gửi lại hoặc đồng thời không tạo capture trùng; transaction number unique. Thu tự động có actor=null, không gán quyền nhân viên cho khách hoặc giả người thu.
- IPN thành công hợp lệ ghi PaymentTransaction, PAID/paid_at; bỏ TTL pending và giữ reservation đến khi xác nhận/xuất hàng. Không tự xuất kho hoặc hoàn tất đơn. Chặn ship đơn VNPay chưa PAID.
- Thành công về muộn sau hủy/hết hạn, hoặc có thêm khoản thu khác: lưu capture/transaction/reference và REVIEW. Không hồi sinh đơn/tồn đã giải phóng. Khoản thu trên đơn chưa trả tiền nhưng không thể đáp ứng chuyển REFUND_PENDING. UI nội bộ chỉ rõ cần kiểm tra hoàn tiền. Hoàn tiền tự động nằm ngoài phạm vi tích hợp này.
- IPN phản hồi 00 xử lý, 02 đã xử lý, 01 không tìm thấy, 04 sai tiền, 97 sai chữ ký/merchant, 99 lỗi xử lý. Query return/IPN được che trong log; không trả hash secret tới frontend.
- QueryDR dùng endpoint sandbox cố định, timeout, không theo redirect; ký chuỗi positional pipe của API tra cứu, kiểm chữ ký phản hồi và ràng buộc merchant/reference/type/số tiền. Chỉ chủ đơn qua POST có CSRF và throttle 10/phút. Trạng thái pending hoặc lỗi tra cứu không tạo capture; thành công dùng chung xử lý atomic/idempotent với IPN, giữ nguyên quy tắc review khi đã hủy/hết hạn. Không giữ khóa DB trong thời gian gọi mạng.

## API

- POST `/api/v1/my-orders/{id}/vnpay/`, body `{bank_mode:""}` mặc định chọn tại cổng; tùy chọn `VNPAYQR` khi provider hỗ trợ. Chỉ owner, kể cả admin cũng không tạo thanh toán thay một customer khác tại route này.
- GET `/api/v1/payments/vnpay/attempts/{reference32}/`: chỉ owner; số tiền, hạn, trạng thái, order_payment_status; payment_url chỉ khi còn có thể thanh toán.
- POST `/api/v1/payments/vnpay/attempts/{reference32}/check/`: chỉ owner + CSRF + throttle; QueryDR có chữ ký, trả cùng cấu trúc trạng thái kèm ưu đãi VNPay đã xác minh. GET không ghi thu tiền.
- GET `/api/v1/payments/vnpay/ipn/`: VNPay gọi server-to-server, không cần phiên đăng nhập.
- GET `/api/v1/payments/vnpay/return/`: VNPay chuyển trình duyệt về `/payments/vnpay/return`; trang này kiểm tra lại session và trạng thái từ DB.
- Order serializer có `vnpay_payment`, ưu tiên giao dịch REVIEW để nhân viên không bỏ sót cảnh báo; không chứa URL/khóa bí mật.

## Bằng chứng và giới hạn

### Tự xác nhận ở trang kết quả — 21/10/2026

Nguyên nhân trước đây: trang kết quả dùng lại thẻ thanh toán, tự đọc database nhưng chỉ gọi QueryDR khi người dùng bấm nút. Nếu IPN thiếu/chậm, trang tiếp tục hiện đang chờ dù giao dịch có thể đã thành công ở VNPay.

`shared/useVnpayResult.js` tự đọc yêu cầu thuộc tài khoản hiện tại, gọi POST QueryDR hiện có nếu còn chờ (tối đa bốn lần trong cửa sổ khoảng 60 giây), xen kẽ GET trạng thái mỗi bốn giây. Các yêu cầu chạy tuần tự; dừng khi có kết quả cuối, mất quyền truy cập, đổi tài khoản hoặc rời trang. Tab ẩn không tự gọi QueryDR; khi quay lại tab trong cửa sổ kiểm tra sẽ tiếp tục. Phản hồi 429 dừng các lần QueryDR còn lại. Giới hạn thời gian không ngắt một yêu cầu mạng đang chạy. Backend vẫn kiểm tra quyền sở hữu, CSRF, chữ ký, số tiền và merchant như trước.

`fe/src/pages/VnpayReturnPage.jsx` và CSS riêng hiển thị kết quả thay cho thẻ bắt đầu thanh toán. Giao dịch đã xác minh hiển thị ngay; giao dịch đang chờ hiển thị tiến trình, không mời thanh toán thêm. Hai ưu đãi được trình bày riêng theo dữ liệu server. Tham số trạng thái trong URL không được dùng để quyết định đã thu tiền. Kiểm thử mới nằm ở `shared/VnpayReturn.test.jsx`.

Xác minh: 103 kiểm thử Vitest qua (gồm 12 ca mới cho trang kết quả); 36 kiểm thử Django `tests.test_vnpay` và `tests.test_portal_sessions` qua trên database riêng `test_tech_retail`; build khách hàng và admin qua; Prettier và kiểm tra khoảng trắng cho mã thay đổi qua. Các ca mới bao gồm tự tra cứu thành công, IPN đến chậm, lỗi mạng, giới hạn thời gian/lượt tra cứu, 429, giao dịch thất bại, giao dịch về muộn cần đối soát, hai ưu đãi, tab ẩn và đổi tài khoản.

Trình duyệt đã xác minh giao diện thành công bằng một giao dịch cũ đã được xác minh, chỉ đọc dữ liệu, không tạo hay thay đổi thanh toán thực. Ảnh: [trang kết quả thành công](screenshots/vnpay-auto-result-success.png). Chuyển trạng thái đang chờ → thành công được kiểm tra bằng API giả lập trong kiểm thử tự động; chưa hoàn tất thêm giao dịch VNPay mới để xác minh toàn luồng. Không thay đổi backend, migration hay cấu hình VNPay cho bản sửa này; Vite đang chạy nhận thay đổi tự động, nếu còn giao diện cũ hãy tải lại mạnh Ctrl+F5.

Cập nhật giao diện 21/10/2026: bỏ chữ “sandbox” khỏi nhãn khách hàng ở checkout, chi tiết đơn và trang kết quả; dịch UNPAID thành “Chưa thanh toán”. Thẻ thanh toán hiển thị trạng thái, số tiền, mã cửa hàng và ưu đãi VNPay đã xác minh; mã yêu cầu nằm trong “Chi tiết giao dịch”. Giữ một dòng nhận biết môi trường thử nghiệm và giữ nguyên endpoint sandbox, biến môi trường, mã phương thức VNPAY_SANDBOX, xử lý IPN/QueryDR cùng database. Đây là thay đổi giao diện và điều hướng, không chuyển sang thanh toán thật.

Xác minh cho thay đổi giao diện này: 80 kiểm thử Vitest và 4 kiểm thử Node đều qua, build khách hàng/admin qua, kiểm tra định dạng và git diff --check qua. Bao gồm điều hướng chỉ một lần bấm, kiểm tra lại yêu cầu cũ, chống bấm lặp, chặn URL lạ, bỏ phản hồi cũ sau đổi tài khoản, trạng thái trả tiền theo server, lỗi mạng cho phép thử lại và hiển thị hai ưu đãi. Các kiểm thử UI dùng API giả lập, không tạo thanh toán hoặc thay đổi đơn thực. Chưa xác minh trực quan hay hoàn tất giao dịch end-to-end cho giao diện mới: trình duyệt tích hợp chặn truy cập tab đang ở trang lỗi theo chính sách URL (không cấp quyền quan sát nội dung).

Tự động: backend có ca chữ ký/sai tiền/merchant/replay/query trùng, owner/CSRF, return giả, hủy/hết hạn/review, chặn thu tay/xuất chưa trả tiền, transaction unique và concurrent start/IPN. UI kiểm tra chỉ dùng host sandbox, trạng thái theo server, lỗi retry và không tạo QR giả.

Browser thử trên test_tech_retail/cổng 8001,5175/cookie riêng: tạo yêu cầu và mở trang QR thật VNPay, số tiền 1.234.000 VND khớp fixture. Không dùng user/giỏ/đơn thực để kiểm thử; không hoàn tất quét/thanh toán ngân hàng. Ảnh `.runtime/vnpay-order-panel.png`, `.runtime/vnpay-qr-sandbox.png`. Các phản hồi IPN trong unit tests là fixture ký bằng khóa test, không phải bằng chứng đã nhận IPN thật từ VNPay.

Cập nhật sau phản hồi người dùng ngày 20/10: người dùng đã thanh toán NCB sandbox. Tra cứu QueryDR thật xác minh giao dịch thành công cùng cả TECH100K và ưu đãi provider 100.000đ, sau đó phục hồi trạng thái đơn bị thiếu IPN bằng cùng quy trình xác thực/ghi thu tiền. Không tạo thanh toán mới hoặc tự đánh dấu PAID bằng dữ liệu trình duyệt. Chưa có bằng chứng nhận IPN tự động cho giao dịch này.

[Tài liệu tích hợp VNPay](https://sandbox.vnpayment.vn/apis/docs/thanh-toan-pay/pay.html), [thông tin thử nghiệm](https://sandbox.vnpayment.vn/apis/docs/gioi-thieu/).
[Tài liệu QueryDR](https://sandbox.vnpayment.vn/apis/docs/truy-van-hoan-tien/querydr%26refund.html).
