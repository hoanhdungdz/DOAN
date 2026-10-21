# Kết quả kiểm thử thực chạy

Ngày kiểm chứng: 13/10/2026. Môi trường Windows, Python 3.14.6, Django 5.2.18, MySQL 8.0.46 (InnoDB), Node 24.18.0. Backend kiểm thử trên database dùng một lần `test_tech_retail`, tách database ứng dụng `tech_retail`.

## Tự động

| Kiểm chứng | Kết quả |
|---|---|
| `manage.py test tests --noinput` từ thư mục be | 101 tests, PASS (cập nhật sau rà soát catalog) |
| `npm.cmd run test:ui` từ root | 4 Node tests + 7 Vitest tests, PASS (cập nhật sau sửa ảnh/responsive) |
| `npm.cmd run build` | Cả fe và admin PASS |
| Django check, makemigrations --check --dry-run | Không lỗi; không thiếu migration |
| spectacular --file openapi.yaml --validate | Schema hợp lệ, không warning/error |
| Ruff check/format và Prettier source | PASS |
| reconcile_inventory trên database ứng dụng | 834 số dư, 0 sai lệch |
| Import dry-run / thật / lặp lại | Rollback 278 / nhập 278 / bỏ qua 278; tồn không nhân đôi |
| SHA256 bản dữ liệu copy | Khớp nguồn; xem DATA_ANALYSIS.md |

Backend kiểm tra session/CSRF, reset token, scope chi nhánh, chống tăng quyền, ownership/PII, giá backend/snapshot, giữ tồn/expiry, hủy/xuất/hoàn tất, thu/hoàn tiền/idempotency, POS atomic, chứng từ kho, điều chuyển, import rollback, OTP, report/CSV, audit và lỗi không lộ nội dung exception. Kiểm tra đồng thời dùng hai kết nối MySQL tranh đơn vị tồn cuối cùng; không dùng SQLite để thay thế khóa MySQL.

Sáu ca mới kiểm tra review catalog dry-run/rollback, giữ nguyên 278 identities/snapshots/tồn/giá, không bán bản trùng đã cách ly, nhãn hàng cũ và danh mục Mac mini qua API, chạy lại/reimport idempotent, bảo vệ chỉnh sửa vận hành và validation tên hàng cũ với tình trạng mới. Trên database ứng dụng đã đối chiếu before/after: 31 chỉnh sửa metadata, 0 conflicts, ledger/giá/snapshot/số dư không đổi. Xem CATALOG_DATA_REVIEW.md.

Frontend kiểm tra tiền bằng đơn vị nhỏ nhất, khóa idempotency, hook tải dữ liệu khi đổi route và khi phản hồi đến sai thứ tự, xác nhận/hủy dialog. Vite đã được kiểm tra trả 403 khi yêu cầu file thử trong .runtime; shared API vẫn tải được. Không sử dụng secrets thật làm file thử HTTP.

## Trực tiếp trên trình duyệt

Fixture được tạo tường minh trong test_tech_retail, mật khẩu ngẫu nhiên lưu riêng trong .runtime. Backend/frontend test chạy cổng 8001/5175/5176, cookie riêng; đã dừng sau kiểm tra, database test được test runner xóa.

Đã kiểm tra đăng nhập Admin/dashboard; tạo và ghi sổ chứng từ nhập; guest checkout iPhone 15 từ chối kho không đủ hàng và thành công ở kho đủ hàng; đơn PENDING → confirm → pack → ship → xác nhận thu COD → complete → xem invoice. Đây là giao dịch kiểm thử local, không có thanh toán ngoài. Ảnh minh chứng trong screenshots/.

Tìm `iphone` trên catalog dữ liệu nguồn trả 16 sản phẩm, không có Watch. Nguyên nhân trước đó là tìm cả thông số tương thích iPhone của Apple Watch; nay search chỉ xét tên/SKU/thương hiệu, spec có bộ lọc riêng.

## Giới hạn nghiệm thu

Chưa hoàn thành UAT toàn bộ vai trò/màn hình/trình duyệt. Override viewport của trình duyệt kiểm thử không có hiệu lực, nên lần sửa responsive sử dụng iframe với viewport CSS thật 320–1920px; xem IMAGE_RESPONSIVE_FIX.md. Cần kiểm tra thêm thiết bị nhỏ thực tế, hộp thoại in/in giấy, mở CSV trong Excel, SMTP/SMS thật, triển khai HTTPS/backup/khôi phục và tải nhiều người dùng trước vận hành.

Google/Facebook/Gemini đang DEFERRED; AI chat trả 503 đúng thiết kế. Email console và SMS development không phải gửi thật. Cache throttle development theo tiến trình, cần cấu hình dùng chung nếu chạy nhiều worker. Không coi build và các tests trên là chứng nhận sẵn sàng production.

## Cập nhật sửa CSRF ngày 19/10/2026

- `npm run test:ui`: 4 Node tests và 24 Vitest tests PASS. Các ca API mới kiểm tra cookie đổi ở tab khác, lấy token trước yêu cầu ghi, dùng chung lần lấy token đang chờ, thử lại đúng một lần cho `CSRF_FAILED`, giữ nguyên body/idempotency key, và không gửi lại khi lỗi mạng/quyền/nghiệp vụ.
- `manage.py test tests.test_runtime tests.test_api.SessionSecurityTests --keepdb --noinput`: 11 tests PASS trên database kiểm thử riêng. Bao gồm chặn CSRF thiếu/cũ, token mới đi qua được bước kiểm tra CSRF, endpoint token không cache và các ca session/login/logout hiện có. Không chạy lại toàn bộ backend suite trong lần sửa này.
- Build cả `fe` và `admin` PASS. Sau bổ sung kiểm tra số điện thoại 9–15 chữ số, build lại `fe` PASS.
- HTTP thực qua proxy 5173: token lệch cookie nhận 403/`CSRF_FAILED`; lấy token mới rồi gửi dữ liệu login trống nhận 400/`VALIDATION_ERROR`, chứng minh yêu cầu qua được CSRF mà không đăng nhập hoặc tạo tài khoản.
- Trình duyệt: nhập 6 chữ số vào ô điện thoại nhận hướng dẫn nhập số điện thoại thay vì dùng mã OTP; nhập số đúng định dạng gửi yêu cầu tra cứu được, không còn lỗi CSRF. Dùng mã đơn kiểm thử không tồn tại, nên ca này không xác nhận việc gửi OTP hoặc quyền xem một đơn thật.

CSRF vẫn được kiểm tra ở backend cho cả yêu cầu ghi của khách chưa đăng nhập; không thêm endpoint công khai đọc OTP.

## Đơn hàng theo tài khoản, bỏ OTP ngày 19/10/2026

Theo yêu cầu mới của người dùng, thay thế luồng guest checkout/tra cứu OTP được mô tả trong các kết quả lịch sử phía trên. Mua online và xem đơn yêu cầu đăng nhập; trang cá nhân chỉ lấy đơn của tài khoản hiện tại. Không di chuyển, nhận sở hữu hoặc xóa đơn cũ theo số điện thoại.

- `manage.py test --keepdb --noinput`: toàn bộ **111 tests PASS** trên MySQL `test_tech_retail`. Có 12 ca mới về quyền cá nhân, chi tiết đầy đủ không OTP, chặn xem/hủy đơn người khác, giới hạn cả tài khoản nhân viên/Admin, checkout gắn tài khoản và API OTP cũ không còn hoạt động. Các ca OTP cũ đã được thay bằng kiểm thử luồng tài khoản.
- `npm run test:ui`: **4 Node tests + 29 Vitest tests PASS**. Năm ca mới kiểm tra chuyển đến login và giữ URL chi tiết, không tải đơn khi chưa có phiên hợp lệ, dùng API cá nhân, xóa nội dung khi đổi tài khoản và chặn đường dẫn quay lại ngoài website.
- `npm run build`: cả khách hàng và nhân viên PASS. Ruff check/format backend/scripts và Prettier các file React thay đổi PASS. `makemigrations --check --dry-run` không thay đổi model; OpenAPI sinh lại và validate không lỗi/warning.
- Sau khởi động lại backend, kiểm tra HTTP thực qua proxy 5173: truy cập danh sách/chi tiết cá nhân khi chưa đăng nhập trả 403; tạo đơn với CSRF hợp lệ nhưng chưa đăng nhập trả 403; ba route OTP request/verify/result cũ đều trả 404.
- Trình duyệt với phiên tài khoản hiện có: `/lookup` tự chuyển đến `/orders`, hiển thị 3 đơn đã gắn tài khoản; chọn Xem chi tiết mở sản phẩm, giá, người nhận, trạng thái thanh toán và tiến trình trực tiếp, không có bước OTP. Không tạo hoặc sửa đơn ứng dụng trong kiểm tra này. Ảnh minh chứng local: `.runtime/account-orders-no-otp.png`.

Bảng OTPChallenge và các file inbox cũ bị Git bỏ qua được giữ để tránh xóa lịch sử; không còn API/adapter sử dụng chúng. Quyền xử lý đơn của nhân viên trong app quản trị vẫn theo chi nhánh; API `my-orders` luôn lọc riêng tài khoản.

## Google Login ngày 19/10/2026

- `manage.py test --keepdb --noinput`: **129 tests PASS** trên MySQL `test_tech_retail`. Có 18 ca mới về Google: state/CSRF/PKCE, callback cùng hostname, JWT ký RSA thật qua google-auth (transport chứng chỉ và token Google dùng fixture test), sai aud/iss/exp/chữ ký/nonce/email_verified/azp, phát lại/phiên hết hạn/phiên khác, hủy/mạng lỗi, tạo customer không nâng quyền, không auto-link email, liên kết rõ giữ User/Customer và không chiếm identity, tài khoản khóa, chặn redirect ngoài và che query log. Sau hoàn thiện handler log chạy lại nhóm Google/runtime **22 tests PASS**.
- `npm run test:ui`: **4 Node tests + 38 Vitest tests PASS**. Chín ca Google mới kiểm tra nút ở login/register khách và không có ở login nhân viên, feature tắt, lỗi start có thể thử lại, thao tác link rõ ràng, chặn authorization URL bất ngờ, chờ session server trước khi gộp giỏ/quay lại đơn, không nhận đăng nhập từ URL success giả, liên kết về profile không merge và khôi phục giỏ khi lỗi; mã lỗi query lạ không làm hỏng trang.
- `npm run build`: cả fe/admin PASS. Ruff check/format, Prettier các file thay đổi và `pip check` PASS. OpenAPI sinh lại/validate không lỗi; makemigrations check không còn thay đổi. Migration `accounts.0002_google_login_attempt` đã áp dụng trên database ứng dụng, không sửa dữ liệu sản phẩm/đơn.
- Browser thực: nút Đăng nhập bằng Google xuất hiện ở `/login?next=%2Forders`; bấm nút mở `accounts.google.com`, hiển thị Sign in để tiếp tục vào **Tech Retail**, với callback 127.0.0.1 đã đăng ký. Ảnh local `.runtime/google-login-button.png` và `.runtime/google-provider-login.png`. Không nhập thông tin tài khoản hoặc đồng ý cấp quyền Google thay người dùng; chưa kiểm thử đổi authorization code thật và hoàn tất phiên bằng Gmail thật.
- HTTP thực: callback không có state hợp lệ chuyển về login an toàn; development access log vẫn ghi yêu cầu và che toàn bộ query callback. Đã kiểm tra secret không xuất hiện trong các file Git nhìn thấy; `.env` và client_secret*.json bị Git bỏ qua. Không lưu token vào browser storage, database hoặc URL hoàn tất.

Cấu hình triển khai/cách liên kết tài khoản cũ: GOOGLE_LOGIN.md. Facebook/Gemini vẫn DEFERRED, không giả đăng nhập/provider thành công.

## Nhập thêm hàng và checkout theo tồn chi nhánh ngày 19/10/2026

- `manage.py test tests --keepdb --noinput` từ be: **135 tests PASS**. Sáu ca mới kiểm tra kho không đủ hàng báo đúng chi nhánh và rollback, metadata inventory vẫn theo scope, phiếu nhập cộng on_hand một lần/giữ nguyên reserved, từ chối nhập ngoài quyền; availability giải phóng đúng PENDING hết hạn và giữ nguyên đơn chưa hết hạn.
- `npm run test:ui`: **4 Node tests + 46 Vitest tests PASS**. Tám ca mới kiểm tra checkout với tồn 3/0, toàn giỏ phải đủ ở cùng kho, thiếu số lượng/sản phẩm ngừng bán, refresh khi tồn thay đổi, lỗi server không gửi lại đơn/xóa giỏ; nhập IN qua chứng từ, retry ghi sổ cùng ID và chặn lượng/lý do không hợp lệ.
- Build fe/admin, Ruff/Prettier, OpenAPI validate và kiểm tra whitespace PASS. Không có thay đổi model/migration ở lần sửa tồn kho này.
- Browser trên fixture test riêng và cookie riêng (8001/5175/5176): lọc SKU-DIE-0052 thấy tên chi nhánh/kho và nút Nhập thêm hàng; checkout chọn sẵn Cầu Giấy còn 3, Hoàng Diệu/Thanh Xuân 0 bị vô hiệu. Từ mục Sản phẩm nhập 5 vào Hoàng Diệu; checkout tải lại, Hoàng Diệu trở thành đủ hàng, chọn nơi này và đặt đơn thành công. Đối chiếu IN +5 một lần, on_hand=5/reserved=1/available=4 và 834 số dư không sai lệch ledger. Đã dừng server test và dọn fixture trước khi chạy lại suite cuối 135 tests.
- Giữ nguyên tồn ứng dụng của SKU trong ảnh: Cầu Giấy 3/Hoàng Diệu 0/Thanh Xuân 0; không nhập số lượng hoặc tạo đơn thử trong database ứng dụng. Sau bổ sung refresh xử lý đơn hết hạn, đã chạy lại suite và build; endpoint availability chạy trên backend chính và từ chối khách chưa đăng nhập dù CSRF hợp lệ.

Ảnh `.runtime/stock-inventory-fixed.png`, `stock-receipt-dialog.png`, `stock-checkout-fixed.png`, `stock-checkout-success-test.png`; hướng dẫn STOCK_CHECKOUT_FIX.md.

## Facebook Login ngày 20/10/2026

- `manage.py test tests --keepdb --noinput` từ be: **150 tests PASS** trên MySQL test_tech_retail. Nhóm Google/Facebook riêng **33 tests PASS**. Có 15 ca Facebook mới: CSRF, callback host, state một lần/expiry/session, provider app/user/type/expiry, lỗi mạng, hủy, email thiếu/trùng, không tự liên kết, liên kết giữ Customer và không chiếm identity, tài khoản khóa và che callback log.
- `npm run test:ui`: **4 Node tests + 52 Vitest tests PASS**. Sáu ca Facebook mới kiểm tra nút khách hàng, ẩn ở nội bộ/provider tắt, lỗi an toàn, destination, link rõ ràng và callback chỉ tiếp tục với session thật.
- `npm run build`: cả fe/admin PASS. Ruff check, OpenAPI validate, makemigrations check PASS. Migration accounts.0003_facebookloginattempt đã áp dụng trên database ứng dụng. Không tạo đơn hay sửa tồn khi kiểm thử Facebook.
- Đã bật Facebook trong be/.env riêng bằng thông tin người dùng cấu hình sẵn, khởi động lại backend; features thực trả facebook_login=true. Nút mở đúng Meta OAuth nhưng Meta trả “Sorry, something went wrong”; chưa có code thật/cấp quyền hoặc đăng nhập Facebook thành công để kiểm chứng. Không coi tests fixture là kết quả provider thật. Ảnh và cách cấu hình tại FACEBOOK_LOGIN.md.

## VNPay sandbox ngày 20/10/2026

- Backend cuối: `manage.py test tests --keepdb --noinput` từ be, **167 tests PASS**, gồm 17 ca VNPay. Có kiểm tra concurrency trên MySQL cho cùng lúc tạo yêu cầu và cùng lúc nhận IPN: một reference khi retry cùng mode, một capture khi IPN trùng. Kiểm tra CSRF/owner, số tiền từ DB, chữ ký, merchant, tham số trùng, time, return không ghi tiền, hủy/expiry/review, transaction number unique và chặn thu tay/xuất chưa trả tiền.
- UI: `npm run test:ui` **4 Node tests + 58 Vitest tests PASS**; build fe/admin PASS; Ruff/OpenAPI validate/makemigrations check PASS. Migration payments.0002_alter_paymenttransaction_actor_vnpayattempt đã áp dụng; dictionary được sinh lại. Đã bật cấu hình riêng và khởi động lại backend, feature vnpay_sandbox=true.
- Browser fixture riêng test_tech_retail, cổng 8001/5175 và cookie riêng: đăng nhập, mở đơn thử, tạo yêu cầu đúng 1.234.000 VND, mở cổng sandbox thực và chọn App Ngân hàng và Ví điện tử để thấy QR thật. Mã VNPAYQR trực tiếp trả lỗi 76 nhưng chọn trên cổng hoạt động; UI cuối dùng luồng này, không truyền bank code mặc định. Ảnh .runtime/vnpay-order-panel.png và vnpay-qr-sandbox.png. Không quét bằng app ngân hàng/thanh toán; chưa hoàn tất giao dịch provider/IPN thật.
- Đã đóng tab/server test, dọn fixture test trước khi chạy suite cuối. Không tạo đơn/capture giả trong database ứng dụng. Tunnel do người dùng chạy vẫn giữ nguyên; public IPN URL trả RspCode 97 khi không có chữ ký (đúng thiết kế), chứng minh endpoint tới được qua HTTPS, không chứng minh merchant đã cấu hình IPN.
- Cần khai báo IPN URL cho merchant VNPay để nghiệm thu thanh toán thực sự trên sandbox. Return không thay thế IPN. API refund tự động và production payment chưa triển khai. Xem VNPAY_SANDBOX.md.

## Mã giảm giá cửa hàng ngày 20/10/2026

- Backend: **179 tests PASS**, gồm 12 ca coupon: tiền server, tỷ lệ/cap/danh mục, hạn mức/đơn đầu, snapshot, idempotency, hủy/hết hạn/thu/hoàn, rollback và hai ca concurrency giữa kho/khách hoặc cùng khách. Có kiểm tra VNPay nhận tiền sau giảm và IPN trùng chỉ chốt một lượt.
- UI: **4 Node + 63 Vitest tests PASS**. Nhóm checkout/coupon 10 tests kiểm tra trạng thái mã, nhập/bỏ mã, gửi code + tổng đã xác nhận, chặn mã sai và bỏ phản hồi preview cũ khi đổi giỏ.
- Build fe/admin, Ruff, OpenAPI validate, migration drift check PASS. Migration orders.0002 đã áp dụng. Chạy seed_coupons tạo ba mã thật trong database local; mỗi mã hiệu lực 30 ngày, 1.000 lượt, mỗi khách 1 lần.
- Browser sau khi người dùng đăng nhập: checkout cho thấy TECH100K giảm 24.990.000đ → 24.890.000đ; CHAO5 bị chặn đúng vì khách đã có đơn, PHUKIEN50K bị chặn vì giỏ không có phụ kiện. Desktop 1440px hiển thị hai cột; điện thoại 390px hiển thị một cột, không tràn ngang. Ảnh `docs/screenshots/checkout-coupons-desktop.png` và `checkout-coupons-mobile.png`.
- Tài khoản đang đăng nhập là khách, truy cập admin bị chặn đúng; CRUD admin và CSRF được kiểm tra tự động. Không tạo đơn hoặc thu tiền trên dữ liệu ứng dụng trong lần kiểm tra giao diện này.
- Bộ máy chủ kiểm thử riêng không được khởi động do phê duyệt tự động từ chối; kiểm tra trình duyệt dùng app local và phiên khách do người dùng đăng nhập. Không đổi mật khẩu hoặc tạo tài khoản kiểm thử trong database ứng dụng.

## Sửa phiên thanh toán và hai ưu đãi VNPay ngày 20/10/2026

- Backend: **185 tests PASS** trên MySQL test_tech_retail. Sáu ca QueryDR mới bao gồm owner/POST/CSRF, chữ ký request theo ngày gốc, chữ ký response/ràng buộc merchant/ref/type/amount, timeout/pending không ghi tiền, IPN/QueryDR lặp chỉ một capture, xử lý tiền về sau hủy và mã cửa hàng + ưu đãi provider không giảm capture hai lần.
- UI: **4 Node tests + 69 Vitest tests PASS**. Có kiểm tra revalidate phiên khi quay lại tab, gom yêu cầu đang chờ, phản hồi cũ không khôi phục tài khoản sau login/logout; xóa dữ liệu/liên kết khi owner rejection hoặc đổi tài khoản; nút kiểm tra gọi POST check và hiển thị hai ưu đãi. Lần chạy mặc định nhiều worker bị timeout khởi động trên máy; chạy toàn bộ Vitest lại với `--maxWorkers=2` qua đủ 13 file.
- Build fe/admin, Ruff check/format, OpenAPI validate và migration drift check PASS. Migration payments.0003 áp dụng trên database ứng dụng, backend được khởi động lại.
- QueryDR thật với giao dịch người dùng đã thanh toán NCB: chữ ký hợp lệ, trạng thái thành công, tổng sau mã TECH100K 16.290.000đ, ưu đãi VNPay CTT0604 100.000đ, sau ưu đãi provider 16.190.000đ. Đơn được phục hồi PAID qua service xác minh, không tạo thanh toán mới hoặc sửa tay cờ PAID. Không có bằng chứng IPN tự động cho giao dịch đó.
- Browser: xác nhận lỗi owner trả thông báo tiếng Việt, không lộ tên model hoặc tiếp tục cho thanh toán đơn của tài khoản khác. Sau khi người dùng đăng nhập đúng chủ đơn, trang kết quả hiển thị PAID, TECH100K −100.000đ, CTT0604 −100.000đ và số tiền sau ưu đãi 16.190.000đ. Bấm kiểm tra gọi QueryDR thành công và giữ kết quả, không xuất hiện nút trả tiền lại. Ảnh `docs/screenshots/vnpay-combined-promotions-desktop.png`. Không tạo phiên giả hoặc đổi mật khẩu để bỏ qua quyền.

## Tách phiên admin và khách ngày 20/10/2026

- Backend **192 tests PASS**. Bảy ca mới dùng cùng một cookie jar trên hai cổng, kiểm tra admin không kế thừa customer, khách không kế thừa admin, login/logout riêng, không làm đổi session/CSRF còn lại, CSRF hai bên không dùng chéo, Host loopback, Origin cho API trực tiếp, chặn CORS từ khách mượn staff session, giữ thuộc tính cookie và quyền owner.
- Ruff và diff check PASS. Không sửa model/migration hoặc mã tính tiền; không cần build lại frontend cho thay đổi middleware này.
- Sau khởi động lại backend, người dùng đăng nhập admin ở tab 5174. Thử đúng link Mở cửa hàng target=_blank: dashboard giữ admin@gmail.com, tab cửa hàng mới vẫn là Dũng Hồ Anh / hoanhdung2710@gmail.com. Không đổi mật khẩu hoặc tạo phiên giả để kiểm tra. Ảnh `docs/screenshots/store-customer-session-isolated.png`.

## Kiểm tra bổ sung phiên admin/khách — 21/10/2026

- Giữ cơ chế middleware hiện có; sửa so khớp cổng HTTPS mặc định và chặn cấu hình frontend trùng. Link Mở cửa hàng lấy CUSTOMER_FRONTEND_URL qua features API thay địa chỉ localhost:5173 ghi cứng.
- Toàn bộ **198 backend tests PASS** trên database test_tech_retail. Chạy lại **13 portal tests PASS** sau bổ sung ca đổi sang tài khoản admin thứ hai. Các ca bắt buộc về ẩn danh/A+B đồng thời/logout/đổi tài khoản/expiry/CSRF/quyền đều có kiểm thử dùng một cookie jar.
- **76 Vitest tests PASS**, build fe/admin PASS; OpenAPI, migration drift, Ruff/Prettier PASS. Không thay model hoặc ghi dữ liệu nghiệp vụ trong database ứng dụng.
- **Chưa xác minh trình duyệt cho bản ngày 21/10**: cơ chế phê duyệt tự động từ chối khởi động môi trường browser riêng với thông báo “blocked by policy”, không có lý do chi tiết. Không tái dùng ảnh cũ để coi là bằng chứng mới. Không chạy đăng nhập provider/thanh toán thật.
- File thay đổi, lệnh kiểm thử, giới hạn và hướng dẫn khởi động/loại bỏ phiên cũ: [PORTAL_SESSIONS.md](PORTAL_SESSIONS.md).

## Đánh giá sản phẩm và hỏi đáp — 21/10/2026

- Thêm đánh giá có xác minh đơn COMPLETED/PAID, ảnh, kiểm duyệt, hỏi đáp/phản hồi, hữu ích và báo cáo. Không thêm dữ liệu người dùng giả từ mockup.
- **217 backend tests PASS** trên test_tech_retail, gồm 19 ca feedback; **91 Vitest tests PASS**, **4 Node tests PASS**. Build fe/admin, OpenAPI validate (0 cảnh báo), migration drift, Django check và Ruff/Prettier/git diff --check qua.
- Kiểm tra API bằng session/CSRF thật trong một cookie jar: khách/admin giữ phiên độc lập, gửi multipart, từ chối khách kiểm duyệt, admin duyệt và khách xem kết quả. Mọi fixture chỉ nằm trong database kiểm thử.
- Đã áp dụng products/0002,0003 và khởi động local; các bảng feedback trong database ứng dụng vẫn trống. Desktop đã xem tab đánh giá/hỏi đáp và admin trống; chưa nghiệm thu gửi/duyệt bằng trình duyệt và chưa xác minh mobile do viewport không đổi kích thước. [Chi tiết và ảnh](PRODUCT_FEEDBACK.md).

## Tự hiển thị kết quả VNPay và kiểm tra trước commit — 21/10/2026

- Trang quay về tự tra cứu QueryDR nếu giao dịch còn chờ, hiển thị kết quả đã xác minh mà không cần bấm kiểm tra. Các yêu cầu chạy tuần tự, giới hạn bốn lần tra cứu trong khoảng một phút; lỗi mạng không bị coi là giao dịch thất bại. Không tự tạo thanh toán khác.
- **217 backend tests PASS** trên database riêng `test_tech_retail`; **103 Vitest tests PASS**, **4 Node tests PASS**. Build khách hàng/admin, Ruff, Prettier cho mã mới và kiểm tra whitespace qua. Bộ giao diện gồm 12 ca mới cho tự xác nhận, IPN chậm, lỗi mạng/429, giới hạn thời gian, đổi tài khoản, hai ưu đãi và kết quả cần đối soát.
- Trình duyệt đã xem trang thành công bằng giao dịch cũ đã được xác minh, chỉ đọc dữ liệu. Chưa hoàn tất thêm giao dịch VNPay mới; luồng đang chờ sang thành công được kiểm tra tự động với API giả lập. [Chi tiết và ảnh](VNPAY_SANDBOX.md).
- Trước commit đã kiểm tra file cấu hình riêng được Git bỏ qua và không tìm thấy giá trị khóa bí mật từ `.env` trong các file đưa vào commit. Không đưa database ứng dụng, `.runtime`, `.env`, thư viện cài đặt hoặc bản build vào Git.
