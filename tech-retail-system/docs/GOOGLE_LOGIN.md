# Đăng nhập Google

Triển khai theo yêu cầu ngày 19/10/2026. Nút Đăng nhập bằng Google có trên trang login/register của ứng dụng khách hàng. Facebook/Gemini vẫn tắt. Không cần Google Maps API.

## Cấu hình máy mới

1. Cài `be/requirements.lock.txt`, chạy `manage.py migrate` để thêm bảng `accounts_googleloginattempt`.
2. Google Auth Platform: tạo OAuth client loại Web application; đăng ký origins và redirect URIs đúng địa chỉ web. Client JSON là dữ liệu cấu hình, không thực thi nội dung; chỉ sử dụng client_id/client_secret/redirect_uris, không lấy endpoint mạng từ JSON.
3. Lưu thông tin riêng trong `be/.env`, không commit JSON hoặc secret. Không đặt secret trong `VITE_*`.

```dotenv
GOOGLE_LOGIN_ENABLED=true
GOOGLE_CLIENT_ID=YOUR_GOOGLE_CLIENT_ID
GOOGLE_CLIENT_SECRET=YOUR_PRIVATE_GOOGLE_SECRET
GOOGLE_REDIRECT_URI=http://localhost:5173/api/v1/auth/google/callback/
GOOGLE_REDIRECT_URIS=http://localhost:5173/api/v1/auth/google/callback/,http://127.0.0.1:5173/api/v1/auth/google/callback/
```

`GOOGLE_REDIRECT_URIS` là danh sách tùy chọn, nếu bỏ trống sẽ dùng URI đơn. Đăng ký cả hai URI và origins tương ứng nếu sử dụng cả localhost/127.0.0.1. Backend chọn callback cùng scheme/host/port với request qua Vite proxy; không đổi hostname giữa luồng để giữ cookie và giỏ local. Cổng 8000 không phải frontend callback mặc định.

4. Khởi động lại Django. `/api/v1/features/` trả `google_login: true` khi đã bật và đủ cấu hình. Thiếu cấu hình thì cờ tắt/nút ẩn hoặc startup báo lỗi rõ; không giả đăng nhập thành công.
5. Mở `/login`, chọn Đăng nhập bằng Google, hoàn tất màn hình Google. Nếu Google yêu cầu quyền thử nghiệm, thêm Gmail vào Audience/Test users. Cần trình duyệt có quyền truy cập tài khoản Google; không cung cấp mật khẩu Google cho website.

## Tài khoản và đơn hàng

- Google subject (`sub`) là danh tính ổn định; SocialIdentity unique(provider, subject). Đăng nhập lại bằng subject đã liên kết dùng đúng User cũ, không gán quyền nhân viên/Admin.
- Email Google phải được xác minh. Email chưa tồn tại: tạo User có mật khẩu không sử dụng được và Customer mới, không có quyền nội bộ.
- Email đã có User nhưng chưa liên kết: dừng với hướng dẫn đăng nhập mật khẩu, vào Hồ sơ cá nhân và chọn Liên kết tài khoản Google. Liên kết là thao tác rõ ràng từ phiên đã đăng nhập; không nhận sở hữu tài khoản chỉ vì email trùng. Giữ User/Customer/hồ sơ/đơn hàng cũ.
- Không chuyển liên kết đã thuộc tài khoản khác, không ghi đè Google khác của cùng tài khoản. Tài khoản bị khóa không đăng nhập được.
- Sau callback, backend tạo phiên Django và chuyển `/auth/google/complete` không kèm token. Frontend chờ `auth/me` xác nhận phiên, gộp giỏ local một lần và trở về orders/cart/checkout/profile hoặc trang chủ. Liên kết chỉ quay lại hồ sơ, không tự gộp giỏ. Lỗi gộp giỏ giữ localStorage để khôi phục.
- App nhân viên vẫn dùng giao diện đăng nhập mật khẩu. Google chỉ giúp xác thực User đã liên kết, không cấp role hoặc chi nhánh mới.

## Xác thực và giới hạn

POST `/api/v1/auth/google/start/` yêu cầu CSRF và throttle auth. Luồng code dùng state ngẫu nhiên, nonce, PKCE S256; state chỉ sống 5 phút và buộc cùng session/người dùng/callback. MySQL khóa và tiêu thụ state trước khi gọi Google, chặn phát lại và callback đồng thời. Nonce/verifier được xóa khỏi bản ghi khi đã dùng; bản ghi hết hạn không có giá trị xác thực. Các bản ghi cũ có thể dọn theo chính sách lưu trữ khi vận hành.

Backend đổi code tại endpoint cố định của Google với timeout; google-auth kiểm tra chữ ký, audience, issuer, iat/exp. Backend kiểm tra thêm nonce, azp nếu có, subject và email_verified. Không lưu access/refresh/ID token trong database, browser storage hoặc trả token qua URL frontend. Endpoint callback không cache, no-referrer; log Django development che query callback. Khi triển khai reverse proxy cần che query callback ở access log của proxy, dùng HTTPS và cấu hình callback/origins phù hợp.

Đã chạy kiểm thử bằng JWT ký RSA thật với khóa test và transport Google được thay bằng fixture trong test. Trình duyệt thực mở được trang Google của Tech Retail bằng client đã cấu hình; chưa thực hiện chọn tài khoản/cấp quyền hoặc đổi authorization code thật thay người dùng.
