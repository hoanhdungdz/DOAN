# Kiểm tra phiên admin và khách — 21/10/2026

## Kết luận và phạm vi

Nguyên nhân gốc của việc cửa hàng nhận tài khoản admin là cookie cùng hostname được chia sẻ giữa các cổng. Mã tại thời điểm kiểm tra đã có PortalCookieMiddleware tách phiên; không tạo thêm cơ chế đăng nhập, không chuyển sang JWT và không đổi database/backend.

Cấu hình thực được đọc từ Django: CUSTOMER_FRONTEND_URL=http://localhost:5173, ADMIN_FRONTEND_URL=http://localhost:5174; cookie gốc sessionid/csrftoken. Database ứng dụng tech_retail và database kiểm thử test_tech_retail tách riêng, trên MySQL 127.0.0.1:3307.

Đã kiểm tra settings.py (thứ tự middleware đúng), shared/api.js (credentials include, lấy CSRF từ API của giao diện hiện tại), shared/session.jsx (kiểm tra lại phiên khi focus/visibility thay đổi, bỏ phản hồi cũ), hai vite.config.js (changeOrigin:false), nút Mở cửa hàng và test_portal_sessions.py. Các phần đã đúng được giữ nguyên.

## Điểm đã sửa

1. So khớp Host/Origin chuẩn hóa cổng mặc định: https://staff.example:443 tương đương https://staff.example. Trước sửa, kiểm thử tái hiện được việc cấp csrftoken thay vì csrftoken_staff trong trường hợp này. Chặn cấu hình hai frontend trùng hostname/cổng vì không thể định tuyến phiên độc lập một cách rõ ràng.
2. Nút Mở cửa hàng trước đây ghi cứng localhost:5173. Nay dùng customer_frontend_url từ GET /api/v1/features/, lấy từ CUSTOMER_FRONTEND_URL của backend. Link mở tab mới với noopener/noreferrer, không thêm query/hash/token, không đăng xuất hoặc sao chép phiên. Cấu hình chưa tải được/không hợp lệ thì chưa cho mở, không chuyển sang một địa chỉ ghi cứng khác.

## Các file thay đổi trong lượt kiểm tra này

- be/common/portal_sessions.py: chuẩn hóa cổng mặc định và từ chối cấu hình trùng.
- be/apps/ai_consultation/api.py: trả URL cửa hàng từ cấu hình qua endpoint features hiện có.
- be/common/schema.py, be/openapi.yaml: mô tả trường cấu hình mới.
- admin/src/components/StorefrontLink.jsx: link cửa hàng chỉ điều hướng tới URL cấu hình hợp lệ.
- admin/src/layouts/AdminLayout.jsx: dùng StorefrontLink thay link ghi cứng.
- be/tests/test_portal_sessions.py: thêm kiểm tra hết hạn hai chiều, tên cookie tùy chỉnh, không tăng quyền, cổng mặc định, cấu hình trùng, URL cửa hàng và đổi tài khoản admin/khách độc lập.
- shared/StorefrontLink.test.jsx: kiểm tra URL cấu hình, target/rel, không truyền credentials/đăng xuất và không mở URL có scheme/query/hash/userinfo không phù hợp.
- Tài liệu: docs/PORTAL_SESSIONS.md, docs/TEST_RESULTS.md, README.md, be/API.md.

Không thay đổi settings.py, shared/api.js, shared/session.jsx, hai vite.config.js hoặc model/migration trong lượt này. Các thay đổi khác đã có trong workspace được giữ nguyên.

## Hợp đồng phiên

- Khách: SESSION_COOKIE_NAME và CSRF_COOKIE_NAME; mặc định sessionid/csrftoken.
- Admin: tên gốc + `_staff`; mặc định sessionid_staff/csrftoken_staff. Không lấy phiên khách làm dự phòng khi admin chưa đăng nhập.
- Host được proxy giữ nguyên để nhận diện frontend. API gọi trực tiếp dùng Origin admin để chọn phiên staff. Request từ Origin khách tới Host admin bị chặn; cookie staff trong cùng trình duyệt không cấp quyền cho request cửa hàng.
- Django vẫn quản lý session, expiry, xoay CSRF, HttpOnly/Secure/SameSite và kiểm tra role/owner. Không thay đổi settings toàn cục theo từng request.
- Login/logout/đổi tài khoản/hết hạn của mỗi giao diện không làm đổi phiên còn lại. Đổi mật khẩu vẫn có thể vô hiệu hóa phiên của cùng người dùng theo quy tắc bảo mật Django; không vô hiệu hóa cơ chế này.

## Bằng chứng kiểm thử

Các lệnh đã chạy:

```powershell
# Working directory: tech-retail-system/be
..\.venv\Scripts\python.exe manage.py test tests --keepdb --noinput
..\.venv\Scripts\python.exe manage.py test tests.test_portal_sessions --keepdb --noinput

# Working directory: tech-retail-system
npx.cmd vitest run --maxWorkers=2
npm.cmd run build
.\.venv\Scripts\python.exe be/manage.py spectacular --file be/openapi.yaml --validate
.\.venv\Scripts\python.exe be/manage.py makemigrations --check --dry-run
```

- Toàn bộ backend: 198 tests PASS trên test_tech_retail, gồm Google/Facebook, giỏ hàng, checkout, kho, coupon và VNPay với provider fixtures.
- Chạy lại nhóm portal sau bổ sung đổi tài khoản admin thứ hai: 13 tests PASS. Một APIClient dùng chung cookie jar cho hai cổng để mô phỏng trình duyệt. Có đủ ca chỉ admin/cửa hàng ẩn danh; A/B đồng thời; đăng xuất/đổi tài khoản hai chiều; hết hạn từng phiên; CSRF dùng chéo bị từ chối; API quản trị từ cửa hàng không được tăng quyền; owner vẫn bị giới hạn.
- Giao diện: 76 Vitest tests PASS trên 14 file. Build fe/admin PASS.
- OpenAPI validate, migration drift, Ruff và Prettier các file thay đổi PASS. Không có migration cần áp dụng.
- Không tạo/sửa/xóa dữ liệu nghiệp vụ trong tech_retail; không gọi Google/Facebook hoặc thanh toán thật. MySQL development 3307 được khởi động để chạy tests; không sửa dịch vụ MySQL khác.

## Phần chưa xác minh trong lượt này

Không có nghiệm thu trực tiếp trên trình duyệt cho bản sửa ngày 21/10. Các cổng ứng dụng chính đang dừng. Lệnh chuẩn bị dữ liệu và khởi động bộ máy chủ browser riêng (8001/5175/5176, database test_tech_retail và cookie riêng) bị cơ chế phê duyệt tự động từ chối trước khi thực thi, với thông báo “blocked by policy”, không có lý do chi tiết. Không thử cách khởi động khác để vượt chặn; không dùng dữ liệu ứng dụng thay thế. Ảnh kiểm tra ngày 20/10 trong TEST_RESULTS là bằng chứng lịch sử, không được coi là ảnh nghiệm thu mới.

Chưa kiểm tra triển khai HTTPS/reverse proxy production, đăng nhập Google/Facebook thật hoặc giao dịch VNPay thật trong lượt này. Các luồng đó được chạy hồi quy bằng fixture trên database kiểm thử.

## Khởi động lại và loại bỏ phiên cũ

1. Dừng các tiến trình backend/frontend development cũ rồi chạy:

```powershell
Set-Location -LiteralPath 'F:\OneDrive\Documents\VPProjects\đồ án\tech-retail-system'
.\scripts\start-local.ps1
```

2. Kiểm tra be/.env có CUSTOMER_FRONTEND_URL=http://localhost:5173 và ADMIN_FRONTEND_URL=http://localhost:5174 tương ứng môi trường. Hai proxy Vite phải tiếp tục giữ changeOrigin:false; trường hợp production cần cấu hình Host/Origin/trusted origins chính xác.
3. Với phiên có từ bản dùng chung cookie: đăng xuất từng giao diện và đăng nhập lại đúng tài khoản. Nếu vẫn còn tài khoản cũ, xóa riêng bốn cookie của localhost (hoặc tên gốc tùy chỉnh tương ứng), tải lại rồi đăng nhập khách ở 5173 và admin ở 5174. Không cần xóa tài khoản, đơn hàng hoặc dữ liệu database.
4. Thử Mở cửa hàng từ admin: cửa hàng phải giữ tài khoản khách; nếu chưa đăng nhập khách thì phải ẩn danh. Thử reload/chuyển tab, đăng xuất/đổi tài khoản từng bên để xác nhận trên trình duyệt đang dùng.
