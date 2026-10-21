# Đăng nhập Facebook

Đã tích hợp ngày 20/10/2026: đăng nhập/đăng ký khách hàng bằng Facebook, liên kết rõ ràng trong Hồ sơ cá nhân, phiên Django và gộp giỏ khách sau đăng nhập. Không thay đổi quyền nhân viên; tài khoản mới chỉ là khách hàng.

## Cấu hình local

Trong `be/.env` (không commit):

```dotenv
FACEBOOK_LOGIN_ENABLED=true
FACEBOOK_APP_ID=<App ID của ứng dụng Meta>
FACEBOOK_APP_SECRET=<App Secret, chỉ đặt ở backend>
FACEBOOK_REDIRECT_URI=http://localhost:5173/api/v1/auth/facebook/callback/
FACEBOOK_GRAPH_VERSION=v25.0
```

Chạy migration `python manage.py migrate` từ `be`, rồi khởi động lại backend. Mở web bằng `http://localhost:5173/login` cho đúng host callback. `127.0.0.1` và `localhost` là hai host/cookie khác nhau; start sẽ báo cấu hình không khớp nếu mở sai host. Khi triển khai HTTPS, cập nhật URI và cấu hình host/proxy/trusted origins phù hợp; URI dùng trên Meta phải khớp chính xác URI backend, cả dấu `/` cuối.

Meta Dashboard → trường hợp sử dụng Facebook Login → Cài đặt: bật Client OAuth, Web OAuth, HTTPS, Strict Mode; dùng luồng redirect nên không cần JavaScript SDK. Đăng ký URI callback trong Valid OAuth Redirect URIs. Nếu Meta thông báo localhost được cho phép tự động ở chế độ phát triển và không cần thêm, làm theo thông báo đó. Không tắt HTTPS/Strict Mode để khắc phục lỗi. Website local chạy HTTP chỉ phục vụ thử nghiệm với loopback; nếu Meta yêu cầu HTTPS thì cần cấu hình địa chỉ HTTPS thật rồi cập nhật callback tương ứng.

Trong Quyền và tính năng, kiểm tra `public_profile` và `email`. Chạy thử bằng tài khoản có vai trò phù hợp trong ứng dụng Meta. Việc phát hành cho người dùng bên ngoài còn phụ thuộc các yêu cầu Meta hiển thị; code không tự công bố ứng dụng hay hoàn thành xét duyệt.

## Hành vi tài khoản

- Chỉ nhận authorization code; backend đổi code, kiểm tra token qua `debug_token` (is_valid, app_id, USER, user_id, hạn token/quyền dữ liệu), lấy `id,name,email` qua Graph API và đối chiếu subject. Có timeout, TLS mặc định, không theo redirect ở request provider; App Secret và token không gửi về frontend hay lưu database.
- State ngẫu nhiên chỉ lưu SHA-256 trong MySQL, dùng một lần trong 5 phút, khóa hàng khi nhận callback. Ràng buộc phiên trình duyệt, tài khoản khởi tạo và URI; POST start được bảo vệ CSRF. Query callback bị che trong log Django.
- Facebook đã liên kết: đăng nhập lại đúng user bằng app-scoped ID, kể cả khi thiếu/đổi email. Không tự nối hai tài khoản theo email.
- Email trùng: đăng nhập tài khoản hiện có bằng mật khẩu hoặc Google, vào Hồ sơ → Liên kết tài khoản Facebook. Giữ nguyên Customer/đơn hàng. Liên kết không thể chiếm identity của người khác hoặc thay Facebook đã liên kết.
- Facebook không cung cấp email: chưa tạo tài khoản mới; hướng dẫn đăng ký/đăng nhập bằng email rồi liên kết Facebook. Không tạo email giả.
- Hủy/timeout/state sai/token không hợp lệ: không đăng nhập, hiển thị lỗi tiếng Việt và cho thử lại. Redirect `next` chỉ chấp nhận các trang nội bộ đã cho phép.

API: `POST /api/v1/auth/facebook/start/` với `{next, link_account}`, `GET /api/v1/auth/facebook/callback/` do Meta gọi. `/features/` cung cấp `facebook_login`, `/auth/me/` có `facebook_linked`. Trang hoàn tất `/auth/facebook/complete` phải có phiên backend thật mới tiếp tục; URL thành công riêng lẻ không đăng nhập được.

## Xác minh

Kiểm thử HTTP provider trong backend dùng response fixture tại ranh giới mạng, không giả đăng nhập thành công trong ứng dụng. Kiểm thử kiểm tra app ID, expiry, subject, state/replay/session/CSRF, trùng email, liên kết và quyền. Đăng nhập/cấp quyền bằng Facebook thật cần người dùng tự hoàn tất trên Meta; chưa có kết quả thật thì không coi là đã kiểm chứng trao đổi code với provider.

Kiểm tra trình duyệt ngày 20/10/2026: nút Facebook hiển thị cạnh Google ở localhost:5173/login; POST start thực tạo state và điều hướng www.facebook.com/v25.0/dialog/oauth với đúng App ID/callback. Meta trả trang chung “Sorry, something went wrong”; không có code callback, chưa xác định nguyên nhân từ thông báo này. Cần kiểm tra tiếp cấu hình ứng dụng Meta và thử bằng trình duyệt/tài khoản có vai trò trong app. Ảnh `.runtime/facebook-login-button.png`, `.runtime/facebook-provider-response.png`. Không nhập thông tin/cấp quyền bằng tài khoản Facebook thay người dùng.

Tài liệu provider: [Manual login flow](https://developers.facebook.com/docs/facebook-login/guides/advanced/manual-flow/), [token inspection](https://developers.facebook.com/docs/facebook-login/guides/access-tokens/debugging-and-error-handling/).
