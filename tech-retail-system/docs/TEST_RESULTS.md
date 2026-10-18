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
