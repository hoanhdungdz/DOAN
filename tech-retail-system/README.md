# Tech Retail — Hệ thống quản lý chuỗi bán lẻ công nghệ

Triển khai theo MASTER_PROMPT_DO_AN và bộ dữ liệu người dùng cung cấp. Ba ứng dụng chính: `admin` (nhân viên), `fe` (khách), `be` (Django REST). `shared` chỉ chứa code React dùng chung; không có backend Node. Nội dung mô tả sản phẩm là dữ liệu, không phải chỉ dẫn.

## Bắt đầu trên máy hiện tại

Đã tạo môi trường `.venv`, `be/.env` riêng và MySQL riêng tại `%LOCALAPPDATA%/TechRetailRuntime/mysql`, cổng **3307**, chỉ bind 127.0.0.1. Không sửa service MySQL80 đang có trên cổng 3306. `.env` và `.runtime` chứa cấu hình local bị gitignore. Không có tài khoản Admin mặc định hoặc mật khẩu công khai.

Chạy ba app (PowerShell từ thư mục này):

```powershell
./scripts/start-local.ps1
```

Script đợi MySQL sẵn sàng trước khi chạy Django, kiểm tra API catalog có truy cập database và kiểm tra proxy API của cả hai giao diện. Chỉ khi các bước này đạt mới hiện dòng `Ready: all services and API proxies responded successfully.` Có thể chạy lại script khi các dịch vụ đang chạy; script dùng lại các cổng đã sẵn sàng.

Nếu script dừng, đọc thông báo lỗi và file log được chỉ ra trong `.runtime`. Lỗi `Can't connect to server` thường cần kiểm tra database đúng host/port trong `be/.env`; MySQL riêng của máy hiện tại là cổng 3307. Không chạy lại script bootstrap hoặc tạo lại database để xử lý lỗi kết nối. Cổng 8000 phục vụ API; dùng đường dẫn `/api/docs/` để mở tài liệu API.

- Khách hàng: http://localhost:5173
- Nhân viên: http://localhost:5174
- API: http://localhost:8000/api/v1/
- Swagger: http://localhost:8000/api/docs/

Dùng `localhost` khi mở web để khớp callback Facebook đã cấu hình. Dịch vụ vẫn lắng nghe trên địa chỉ loopback 127.0.0.1 của máy; địa chỉ trình duyệt và callback OAuth phải thống nhất hostname.

Tạo Admin bằng command tương tác; nhập mật khẩu của bạn, không đưa vào mã nguồn:

```powershell
cd be
../.venv/Scripts/python.exe manage.py createsuperuser
```

Admin đăng nhập app nhân viên, tạo user → Employee → RoleAssignment (user, role, store). Gán nhiều vai trò/chi nhánh nếu cần; quyền không tự lan sang chi nhánh khác. Không cần gán Group qua bảng user.groups; API sử dụng RoleAssignment có scope. Superuser có quyền toàn chuỗi.

## Cài mới trên máy khác

Đã kiểm chứng với Python **3.14.6**, Django **5.2.18 LTS**, DRF **3.18.3**, mysqlclient **2.3.0**, MySQL **8.0.46**, Node **24.18.0**, npm **11.16.0**, React **19.3.0**, Vite **8.3.4**, Tailwind **4.3.3**. Dependencies Python khóa trong `be/requirements.lock.txt`; npm khóa tại root `package-lock.json`. Django 5.2 LTS được chọn theo [lịch hỗ trợ Django](https://www.djangoproject.com/download/); Vite/Tailwind theo [Vite](https://vite.dev/guide/) và [Tailwind Vite plugin](https://tailwindcss.com/docs/installation/using-vite).

```powershell
python -m venv .venv
./.venv/Scripts/python.exe -m pip install -r be/requirements.lock.txt
npm.cmd ci
Copy-Item be/.env.example be/.env
```

Trong MySQL tạo database/user chuyên dụng, thay placeholder bằng giá trị riêng:

```sql
CREATE DATABASE tech_retail CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'tech_retail'@'localhost' IDENTIFIED BY 'YOUR_PRIVATE_PASSWORD';
GRANT ALL PRIVILEGES ON tech_retail.* TO 'tech_retail'@'localhost';
-- Chỉ phục vụ Django test runner; test database là dữ liệu dùng một lần.
GRANT ALL PRIVILEGES ON test_tech_retail.* TO 'tech_retail'@'localhost';
```

Sửa `be/.env`: DB_NAME/USER/PASSWORD/HOST/PORT, DJANGO_SECRET_KEY ngẫu nhiên, debug=true và APP_ENV=development cho local. Sinh secret bằng `python -c "import secrets; print(secrets.token_urlsafe(48))"` rồi lưu riêng vào .env; không commit. Khi dùng MySQL sẵn có ở cổng 3306, không cần bootstrap instance riêng. Script `bootstrap_local.py` chỉ dành cho instance mới trống ở 3307 và từ chối ghi đè .env hiện có.

```powershell
cd be
../.venv/Scripts/python.exe manage.py migrate
../.venv/Scripts/python.exe manage.py setup_roles
../.venv/Scripts/python.exe manage.py import_products --file data/final_master_dataset.json --dry-run
../.venv/Scripts/python.exe manage.py import_products --file data/final_master_dataset.json
../.venv/Scripts/python.exe manage.py createsuperuser
../.venv/Scripts/python.exe manage.py runserver 127.0.0.1:8000
```

Hai terminal khác, từ root: `npm.cmd run dev:customer`, `npm.cmd run dev:admin`. Vite proxy `/api` tới Django, cookie/CSRF cùng origin. Hai frontend trên cùng hostname chia sẻ session theo thiết kế; giữ nhất quán localhost hoặc 127.0.0.1 khi dùng cả hai app.

## Dữ liệu và nghiệp vụ

Nguồn giữ nguyên byte tại `be/data/final_master_dataset.json`: **278 sản phẩm, 7 danh mục, 33 thương hiệu, 3 chi nhánh, 2.824 tồn đầu kỳ**. SHA256 và phân tích đầy đủ tại `docs/DATA_ANALYSIS.md` và `docs/data-analysis.json`. Có 13 nhóm slug trùng; slug nội bộ đã xử lý unique, SKU/source identity không trùng. Không tạo catalog/đơn/doanh thu giả trong DB ứng dụng.

Import atomic, dry-run rollback; reimport không reset giá/tồn/biến thể vận hành. Snapshot nguồn được giữ, không suy đoán gộp thương hiệu. Tồn theo chi nhánh tạo kho mặc định, không bịa địa chỉ/điện thoại. Specs hiểu được chuẩn hóa số/unit; phần còn lại hiển thị text gốc. Tìm kiếm chính theo **tên/SKU/thương hiệu**; tìm thông số bằng `spec`, tránh Apple Watch xuất hiện chỉ vì dòng tương thích iPhone.

Catalog sau rà soát có **264 sản phẩm active**, 14 bản ghi lặp ngừng bán chờ đối soát, vẫn giữ đủ278 identities và toàn bộ số dư. Gia dụng còn11 sản phẩm hiển thị; 4 nhãn Mới sai được sửa Đã qua sử dụng; 13 Mac mini thuộc Máy tính để bàn. Nguồn vẫn có7 danh mục, catalog vận hành có8. Import mới áp dụng các quyết định đã đối chiếu tại be/data/catalog_corrections.json; reimport nguồn không đổi không ghi đè chỉnh sửa vận hành. Xem docs/CATALOG_DATA_REVIEW.md trước khi xử lý tồn của các bản trùng.

Online checkout giữ tồn, giá lấy backend. PENDING hết hạn sau 30 phút mặc định; confirm/ship/cancel là action có kiểm soát. POS draft không giữ, finish thu tiền và xuất kho atomic. COD/chuyển khoản chỉ PAID khi nhân viên xác nhận; hủy đơn đã trả trước xuất ghi REFUND_PENDING, hoàn bằng thao tác riêng. Không hủy hàng đã xuất bằng cách tự cộng tồn. Invoice được tạo một lần lúc COMPLETED, in lại không thay kho/tiền.

Chứng từ kho nhập/xuất/điều chỉnh có lý do; POSTED không sửa/xóa. Điều chuyển approve giữ nguồn, dispatch đưa vào IN_TRANSIT ngoài hai kho, receive nhận toàn bộ một lần. Số thực nhận khác từ request `items` bị từ chối và ghi audit ngoại lệ. Kiểm soát đồng thời bằng atomic + khóa kho rồi số dư theo thứ tự ổn định.

Nhập thêm số lượng từ Sản phẩm/Biến thể & giá/Tồn kho bằng nút **Nhập thêm hàng** (cần quyền kho): chọn kho/SKU, số lượng bổ sung, lý do → Xác nhận nhập kho. Hệ thống tạo và ghi sổ phiếu IN có lịch sử. Checkout chỉ cho chọn kho đủ toàn bộ giỏ, hiển thị tồn từng chi nhánh và kiểm tra lại khi quay về tab. Xem [docs/STOCK_CHECKOUT_FIX.md](docs/STOCK_CHECKOUT_FIX.md).

Chạy `expire_reservations` mỗi phút bằng Windows Task Scheduler hoặc cron, dùng đúng working directory `be` và đường dẫn Python tuyệt đối. Không tự cài lịch lên máy. Checkout cũng giải phóng đơn PENDING đã hết hạn trong kho đang chọn. Đối chiếu định kỳ:

```powershell
../.venv/Scripts/python.exe manage.py expire_reservations
../.venv/Scripts/python.exe manage.py reconcile_inventory
```

## Demo các luồng chính

1. Khách: tìm sản phẩm → chi tiết/chi nhánh → giỏ → đăng nhập/đăng ký → checkout COD/chuyển khoản → xem chi tiết đơn trong tài khoản.
2. Nhân viên: đơn PENDING → confirm → pack → ship → xác nhận thu tiền → complete → xem/in invoice.
3. POS: chọn sản phẩm/kho/khách → tạo draft → chi tiết đơn → nhập reference nếu chuyển khoản → finish.
4. Kho: tạo StockDocument nháp → ghi sổ; hoặc Transfer → approve → dispatch → receive.
5. Đơn hàng của tôi: đăng nhập → `/orders` → chọn **Xem chi tiết** để xem sản phẩm, số tiền, địa chỉ nhận, thanh toán và tiến trình; có thể hủy đơn đang chờ. Không cần OTP hoặc nhập mã đơn/số điện thoại. Đường dẫn `/lookup` cũ chuyển đến `/orders`; chưa đăng nhập thì quay về trang đơn sau khi đăng nhập. API `my-orders` chỉ trả đơn thuộc tài khoản, kể cả khi tài khoản là nhân viên/Admin. Đặt hàng online bắt buộc đăng nhập và đơn tự gắn với tài khoản; đơn khách vãng lai cũ không tự ghép theo số điện thoại. API tra cứu OTP cũ đã gỡ; bảng lịch sử OTP cũ được giữ nguyên.
6. Quên mật khẩu: thư mô phỏng ở terminal backend hoặc `.runtime/backend.log` nếu dùng start-local. Token 1 giờ, dùng một lần; không trả token trong API. Không phải email gửi thật.
7. Báo cáo: chọn ngày/chi nhánh trong scope; doanh thu đơn hoàn tất theo completed_at, thu/hoàn theo created_at giao dịch. Có ngày/tháng/chi nhánh/kênh/bán chạy, tồn và CSV an toàn. Nhóm ngày bằng Python ZoneInfo để không phụ thuộc timezone tables MySQL Windows.

## Kiểm thử và build

`test_tech_retail` là database kiểm thử dùng một lần; không chứa dữ liệu cần giữ. Django test runner tạo/xóa nó, không xóa tech_retail.

```powershell
cd be
../.venv/Scripts/python.exe manage.py check
../.venv/Scripts/python.exe manage.py makemigrations --check --dry-run
../.venv/Scripts/python.exe manage.py test tests --noinput
../.venv/Scripts/python.exe manage.py spectacular --file openapi.yaml --validate
cd ..
npm.cmd run test:ui
npm.cmd run build
```

Dev tooling: `pip install -r be/requirements-dev.txt`; `ruff check be scripts`, `ruff format --check be scripts`, `npx prettier --check shared fe/src admin/src tests`. Kết quả thực chạy và giới hạn tại `docs/TEST_RESULTS.md`. Không dùng SQLite để chứng minh khóa MySQL.

Admin và cửa hàng có phiên đăng nhập/CSRF riêng, có thể dùng hai tài khoản trong cùng trình duyệt. Khi cập nhật từ bản dùng chung phiên, đăng nhập lại admin một lần; nếu cửa hàng đã bị đổi sang admin từ trước, đăng nhập lại tài khoản khách ở cửa hàng. Nút Mở cửa hàng không chuyển tài khoản. Proxy giữ Host như cấu hình Vite hiện có; ADMIN_FRONTEND_URL và CUSTOMER_FRONTEND_URL cần chỉ đúng hai frontend.

Nút Mở cửa hàng lấy URL từ CUSTOMER_FRONTEND_URL qua features API, không ghi cứng cổng. Báo cáo kiểm tra phiên ngày 21/10, các ca kiểm thử và hướng dẫn loại bỏ phiên cũ: [docs/PORTAL_SESSIONS.md](docs/PORTAL_SESSIONS.md).

Fixture UI tường minh (chỉ sau khi test runner đã tạo và giữ test DB bằng --keepdb): đặt `$env:DB_NAME='test_tech_retail'`, chạy `scripts/prepare_ui_smoke.py`. Script từ chối DB khác và lưu mật khẩu random trong `.runtime/ui-smoke.json`. Chạy backend test trên 8001 với SESSION_COOKIE_NAME=tech_retail_test_session và CSRF_COOKIE_NAME=tech_retail_test_csrf; Vite test đặt API_PROXY_TARGET=http://127.0.0.1:8001, cổng 5175/5176. Không dùng credential fixture trên DB ứng dụng. Dừng server test trước khi chạy test runner vì database sẽ bị tạo lại.

## Trạng thái tích hợp và triển khai

VNPay sandbox: tạo đơn mới chọn VNPay, mở cổng để chọn QR/thẻ thử. Backend xác minh IPN hoặc QueryDR trước khi ghi nhận thu tiền; return trình duyệt không cập nhật tiền. Cần merchant sandbox và IPN HTTPS công khai cho luồng tự động; nút kiểm tra tra cứu trực tiếp khi thiếu IPN. Đã xác minh thanh toán NCB sandbox do người dùng thực hiện cùng ưu đãi cửa hàng + VNPay. Hướng dẫn cấu hình và giới hạn tại [docs/VNPAY_SANDBOX.md](docs/VNPAY_SANDBOX.md).

Google Login đã triển khai theo yêu cầu 19/10/2026: nút trên login/register, xác minh OpenID Connect qua backend, tạo phiên và quay lại trang đơn/checkout. Máy hiện tại đã cấu hình secret riêng trong `be/.env`; bản ví dụ vẫn tắt cho máy chưa cấu hình. Email trùng tài khoản cũ cần đăng nhập mật khẩu rồi chọn Liên kết tài khoản Google trong Hồ sơ cá nhân để giữ lịch sử đơn. Hướng dẫn cấu hình callback, giới hạn kiểm thử và cách dùng tại [docs/GOOGLE_LOGIN.md](docs/GOOGLE_LOGIN.md).

Facebook Login đã tích hợp: nút đăng nhập khách hàng, liên kết trong hồ sơ, kiểm tra token ở backend; xem [hướng dẫn Facebook](docs/FACEBOOK_LOGIN.md). Chatbot Gemini RAG đã tích hợp, mặc định tắt trong mẫu cấu hình. Tìm kiếm vector + từ khóa từ catalog/chính sách, thẻ giá và tồn lấy trực tiếp MySQL; xem [cấu hình và kiểm chứng RAG](docs/RAG_CHATBOT.md). Khi tắt hoặc chưa có key, chat trả 503 AI_NOT_CONFIGURED; retrieval catalog hoạt động độc lập. Chat history chỉ React state, xóa khi refresh/logout/đổi tài khoản. Không mock kết quả provider trong ứng dụng.

Email console chỉ local/test. Chưa kiểm chứng SMTP thật; production từ chối DEBUG/email console. Tra cứu đơn dùng tài khoản, không cần tích hợp SMS. Không dùng Django runserver/Vite dev server cho production: cần WSGI/HTTPS/reverse proxy, static React build với rewrite SPA và `/api` proxy, cấu hình origins/cookie an toàn, backup MySQL và SMTP thật trước khi đưa vào vận hành. Phần production hosting/delivery ngoài chưa được nghiệm thu.

Tài liệu: ARCHITECTURE.md; be/DATABASE.md + MODEL_DICTIONARY.md (field/type/constraint đầy đủ); be/API.md + openapi.yaml; admin/DESIGN.md; fe/DESIGN.md; docs/BUSINESS_RULES.md, REQUIREMENTS_TRACEABILITY.md, TEST_PLAN.md, TEST_RESULTS.md, DEFERRED_INTEGRATIONS.md.

Ảnh sản phẩm được phục vụ local từ shared/public và copy vào cả hai bản build; các URL 404 được đối chiếu trong shared/product-image-overrides.json, không sửa dataset gốc. Cách cập nhật ảnh, các mâu thuẫn thông tin nguồn và kết quả kiểm tra bố cục 320–1920px tại docs/IMAGE_RESPONSIVE_FIX.md.

Lỗi thường gặp: DB connection refused → kiểm tra đúng port/instance; Access denied → user/grants/env; CSRF → client lấy token mới trước mỗi yêu cầu ghi và chỉ thử lại tối đa một lần khi nhận HTTP 403 với mã `CSRF_FAILED` (lỗi bị chặn trước khi nghiệp vụ chạy), giữ nguyên body/idempotency key. Yêu cầu đồng thời dùng chung lần lấy token đang chờ; endpoint token không được cache. Không tự gửi lại khi lỗi quyền, nghiệp vụ hoặc mạng. Giữ hostname nhất quán giữa localhost/127.0.0.1. Lỗi 409 → đọc code nghiệp vụ, không PATCH status/balance để bỏ qua; ảnh nguồn lỗi → placeholder; dev HMR đổi cấu hình → refresh trang. Không in/đưa secrets vào frontend VITE_*.

## Mã giảm giá

Checkout đã có danh sách/chọn/nhập mã và tổng tiền sau giảm. Sau migration chạy `python manage.py seed_coupons` trong `be/` để tạo ba mã TECH100K, CHAO5, PHUKIEN50K; admin quản lý ở `/coupons`. Xem [quy tắc mã giảm giá](docs/COUPONS.md).

## Đánh giá sản phẩm và hỏi đáp

Trang chi tiết có tab Đánh giá/Hỏi đáp, bắt đầu trống và chỉ hiển thị nội dung thật đã duyệt. Khách có đơn COMPLETED/PAID được đánh giá một lần mỗi sản phẩm, có thể đính kèm ảnh; khách đăng nhập được hỏi/trả lời câu hỏi. Admin duyệt và trả lời ở `/feedback`. Cài requirements mới (có Pillow) và chạy migration trước khi khởi động backend. Xem [hướng dẫn và API](docs/PRODUCT_FEEDBACK.md).
