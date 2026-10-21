# Trạng thái tích hợp

VNPay sandbox đã tích hợp ngày 20/10/2026: HMAC-SHA512, IPN atomic/idempotent, return chỉ đọc và QR thực trên cổng provider đã hiển thị. Merchant/key đã cấu hình riêng. Chưa có xác nhận khai báo IPN merchant hoặc giao dịch provider hoàn tất; cần bước này trước khi coi tự động thanh toán đã nghiệm thu. Không tích hợp tiền thật/production/refund API. Xem VNPAY_SANDBOX.md.

Google Login đã triển khai theo yêu cầu 19/10/2026: Authorization Code + PKCE S256, state MySQL dùng một lần trong 5 phút, nonce và xác minh ID token bằng google-auth; session Django, không tự liên kết bằng email. Thông tin client được cấu hình riêng ở backend; xem [GOOGLE_LOGIN.md](GOOGLE_LOGIN.md). Kiểm thử provider dùng token RSA thật với khóa test; browser thực mở được màn hình Google, chưa hoàn tất đăng nhập/cấp quyền bằng tài khoản thật thay người dùng.

Facebook Login đã triển khai ngày 20/10/2026: Authorization Code, state MySQL một lần gắn với session, kiểm tra token/app/user/expiry qua Graph API; đăng nhập và liên kết tài khoản rõ ràng. Cấu hình backend và giới hạn kiểm chứng tại [FACEBOOK_LOGIN.md](FACEBOOK_LOGIN.md). Token/secret không gửi frontend. Gemini vẫn **DEFERRED**, bật cờ bị từ chối rõ ràng.

Gemini cần key và model còn hỗ trợ tại thời điểm tích hợp. Luồng: validate câu hỏi/context giới hạn -> retrieval DB top candidates -> provider -> validate schema, candidate IDs và structured claims -> render giá/thông số/tồn từ DB. Không gửi PII, không SQL/tool actions từ model, không lưu lịch sử chat. Interface hiện tại chỉ disabled; kiểm thử nó không chứng minh Gemini chạy thật.

Email local dùng console backend, reset token chỉ trong thư mô phỏng ở terminal; production bắt buộc SMTP thật, TLS, from-address. Chưa kiểm thử gửi email thật. Production từ chối debug/email console. Theo yêu cầu ngày 19/10/2026, tra cứu đơn yêu cầu đăng nhập tài khoản và không dùng OTP; adapter SMS development và các API tra cứu OTP đã gỡ, không cần SMS provider cho luồng này.
