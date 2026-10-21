# Thiết kế API v1

Base `/api/v1/`, JSON, session cookie HttpOnly; GET auth/csrf trả csrfToken, request POST/PATCH/DELETE gửi X-CSRFToken. GET auth/me trả user/permissions/scopes. Credentials include. Tất cả lỗi gồm code/message/fields/request_id; Decimal là chuỗi, datetime ISO8601 có timezone. Pagination page/page_size (max 100), response count/next/previous/results.

Phiên admin/khách độc lập: Host của ADMIN_FRONTEND_URL (proxy giữ Host) chọn cookie gốc + hậu tố `_staff` cho cả session và CSRF; Host CUSTOMER_FRONTEND_URL dùng cookie gốc. Với API khác origin, Origin admin chọn cookie staff. Không lấy cookie khách làm dự phòng cho admin, và chặn request từ Origin khách đến Host admin để tránh mượn phiên qua CORS. HttpOnly/Secure/SameSite, xoay token, owner/role checks giữ nguyên. Đăng nhập/đăng xuất chỉ tác động giao diện đang dùng. Mở cửa hàng là điều hướng thông thường, không truyền session/token qua URL.

GET features còn trả customer_frontend_url lấy từ CUSTOMER_FRONTEND_URL để nút Mở cửa hàng không phụ thuộc cổng ghi cứng. Middleware chuẩn hóa cổng HTTP/HTTPS mặc định và từ chối hai frontend trùng hostname/cổng. Chi tiết kiểm tra và giới hạn tại docs/PORTAL_SESSIONS.md.

| Endpoint | Methods/actions | Quyền |
|---|---|---|
| auth/csrf,features | GET | Public |
| auth/register,login,forgot-password,reset-password | POST | Public + CSRF + throttle |
| auth/logout,change-password | POST | Đã đăng nhập |
| auth/me,profile | GET/PATCH | Chính mình |
| auth/google/start | POST | Public + CSRF + auth throttle; link_account=true bắt buộc đăng nhập |
| auth/google/callback | GET | Google callback; state MySQL dùng một lần, session/người dùng/nonce/PKCE và ID token được xác minh |
| auth/facebook/start | POST | Public + CSRF + auth throttle; link_account=true bắt buộc đăng nhập |
| auth/facebook/callback | GET | Facebook callback; state MySQL một lần gắn session/user/callback, kiểm tra token/app ID/user/expiry qua Graph API |
| products,variants,categories,brands,stores | GET | Public active catalog |
| products,variants,categories,brands,stores,warehouses,suppliers | POST/PATCH | Admin catalog; kho theo scope |
| users,roles,permissions,assignments | GET/POST/PATCH | Admin |
| employees,customers | GET/PATCH | Nội bộ có scope; manager không đổi quyền |
| inventory,movements,reservations | GET | Nội bộ đúng scope; không PATCH balances |
| stock-documents | GET/POST/PATCH; POST /id/post,cancel | Quyền kho đúng chi nhánh |
| stock-transfers | GET/POST; POST /id/approve,dispatch,receive,cancel | Nguồn approve/dispatch; đích receive |
| carts | GET; POST merge; PUT items; DELETE item | Customer |
| carts/availability | POST | Đã đăng nhập + CSRF; snapshot tồn cho giỏ, giải phóng giữ chỗ hết hạn ở kho active liên quan |
| orders | GET/POST; GET /id; POST /id/confirm,pack,ship,complete,cancel,finish | Bắt buộc đăng nhập; ONLINE tự gắn tài khoản; owner read; staff scope |
| my-orders | GET; GET /id; POST /id/cancel | Bắt buộc đăng nhập; chỉ customer.user là chính mình, không mở rộng bằng quyền chi nhánh/Admin |
| payments | GET/POST capture,refund | Sales/manager scope; khách không ghi tiền |
| my-orders/{id}/vnpay | POST | Owner + CSRF + throttle; tạo/reuse URL sandbox từ số tiền server |
| payments/vnpay/attempts/{reference32} | GET | Owner; trạng thái từ DB |
| payments/vnpay/attempts/{reference32}/check | POST | Owner + CSRF + throttle; QueryDR ký server, đối chiếu và phục hồi xác nhận thiếu IPN |
| payments/vnpay/ipn | GET | Provider, chữ ký bắt buộc; xử lý atomic/idempotent, trả RspCode |
| payments/vnpay/return | GET | Kiểm tra checksum, redirect frontend; không ghi thu tiền |
| invoices | GET | Owner hoặc nhân viên scope; tạo từ complete |
| reports/summary,inventory,export | GET | Permission + scope + dates |
| audit-logs | GET | Manager/Admin scope |
| ai/retrieval | GET | Public, filters catalog; không PII |
| ai/chat | POST | 503 AI_NOT_CONFIGURED |

Checkout (đã đăng nhập): `{warehouse: ID, recipient_name, phone, address, fulfillment: DELIVERY|PICKUP, payment_method: COD|BANK_TRANSFER, items:[{variant:ID,quantity:1}]}` và header Idempotency-Key UUID. POS thêm channel IN_STORE, CASH hoặc BANK_TRANSFER (nhân viên có quyền); draft chưa giữ. Thao tác trạng thái có `{reason}`; thu/hoàn có `{order,reference}` và Idempotency-Key. Chứng từ `{warehouse,kind:IN|OUT|ADJUST,reason,supplier?,items:[{variant,quantity}]}`; ADJUST quantity là delta signed khác 0. Transfer `{source,destination,reason,items}`.

`my-orders` hỗ trợ pagination và `search` theo mã đơn trong các đơn sở hữu. Chi tiết trả sản phẩm, giá, người nhận, địa chỉ, thanh toán và lịch sử. Đơn không thuộc tài khoản trả 404; chưa đăng nhập trả 403 theo session authentication. Hủy dùng POST `/my-orders/{id}/cancel/` với `{reason}`; chủ đơn chỉ hủy khi PENDING. Các route `/order-lookup/request/`, `/verify/`, `/result/` cũ đã gỡ (404); session grant cũ không cấp quyền. Không tự liên kết đơn khách vãng lai cũ theo số điện thoại.

Checkout online còn nhận payment_method=VNPAY_SANDBOX khi cấu hình sẵn sàng. Đơn loại này chỉ thu qua IPN hoặc QueryDR đã xác minh chữ ký, không gọi payments CAPTURE/REFUND thủ công; chưa triển khai refund API provider. Trạng thái attempt có promotion_code, promotion_amount (VND), customer_amount = amount - promotion_amount; amount vẫn là tổng đơn sau mã cửa hàng. Xem docs/VNPAY_SANDBOX.md.

Catalog filters: search,category,brand,store,price_min,price_max,condition,in_stock,spec; sort price/-price/name. Báo cáo start/end ISO date inclusive theo giờ Việt Nam, store filter không vượt scope. CSV chống formula injection. Validation/concurrency conflict 400/409, không quyền 403 hoặc hidden object 404, throttle 429, disabled 503.

Google start nhận `{next?,link_account?:false}`, trả `{authorization_url}`. Callback nhận code/state từ Google, tạo session và redirect `/auth/google/complete?next=...&linked=0|1`; không trả token/secret qua URL frontend. Lỗi chuyển login/profile với `google_error` là mã cố định, không chứa phản hồi provider. User payload bổ sung `google_linked`; features trả google_login theo cấu hình backend. Xem docs/GOOGLE_LOGIN.md cho liên kết tài khoản cũ và bảo vệ state/token. Callback là redirect trình duyệt, không phải endpoint JSON.

Facebook start có cùng input/output với Google; callback chuyển `/auth/facebook/complete`, lỗi dùng `facebook_error`. User payload có `facebook_linked`, features có `facebook_login` theo cấu hình. Token chỉ ở backend; không tự liên kết email trùng, thiếu email cần đăng nhập bằng phương thức khác rồi liên kết Facebook. Xem docs/FACEBOOK_LOGIN.md.

`search` chỉ tên/SKU/thương hiệu; `spec` riêng cho text thông số. Không có parser câu hỏi tự nhiên tổng quát. Filters số chuẩn hóa dùng spec_definition + spec_min/spec_max, bắt buộc spec_unit để tránh so sánh nhầm GB/MB. Lọc price/condition/stock phải khớp cùng một variant, không gộp điều kiện từ các variant khác nhau. `internal=true` chỉ có hiệu lực khi là Admin; client không thể dùng nó để xem catalog ẩn.

POS có thể gửi thêm `customer: ID` để chọn khách hàng đã tồn tại: Admin toàn chuỗi, nhân viên chỉ khách có lịch sử đơn tại chi nhánh đang bán. Không tự liên kết theo số điện thoại; ONLINE không được ghi đè customer. Không capture tiền cho POS DRAFT qua payments; dùng action finish để thu tiền và xuất kho trong cùng transaction. Store/warehouse hỗ trợ scope=sales|stock|reports cho danh sách lựa chọn theo quyền. Images/spec metadata cho phép Admin DELETE; chứng từ và lịch sử giao dịch không xóa.

Cart GET/PUT/POST trả `{items:[{variant,quantity,details}],warnings:[]}`. Merge cộng số lượng có hạn mức, revalidate active variant và tồn hiện tại; bỏ dòng đã ngừng bán kèm cảnh báo, vượt tổng tồn được cảnh báo, không tự cắt số lượng hoặc giữ hàng. Checkout vẫn kiểm tra đủ hàng tại một kho. Báo cáo summary bổ sung monthly/by_store/by_channel; tồn là số dư hiện tại, không phải tồn tại thời điểm lịch sử cuối bộ lọc.

Catalog sau review nguồn có nhóm Máy tính để bàn và condition Đã qua sử dụng. Variant write từ chối condition bắt đầu bằng Mới khi tên product ghi Cũ; product write từ chối tên Cũ nếu vẫn có variant active mang condition Mới. Các Product lặp đã cách ly có is_active=false nên không xuất hiện ở API public/variants, không nhận checkout mới; Admin internal vẫn đọc và phục hồi được. Xem docs/CATALOG_DATA_REVIEW.md.

OpenAPI thực tế tại `openapi.yaml`, sinh bằng spectacular --validate, Swagger tại /api/docs/. Auth dùng action path với payload phụ thuộc action được mô tả bên trên. Throttle mặc định auth 10/phút và giới hạn API theo user/IP; cache local theo tiến trình trong cấu hình development hiện tại, reset cooldown được lưu MySQL. Khi triển khai nhiều worker cần cache/throttle dùng chung (có thể database cache), không coi cấu hình development là rate limit toàn cụm.

## Mã giảm giá cửa hàng

`POST /api/v1/checkout/promotions/` nhận `{items: [{variant, quantity}], coupon_code?: string}` từ khách đăng nhập, yêu cầu CSRF. Trả danh sách mã kèm eligibility/reason, mã áp dụng và tổng tiền từ backend; không giữ lượt. `orders/` nhận thêm `coupon_code` và `quoted_total` (tùy chọn) để kiểm tra lại trước khi tạo đơn. Tổng tiền preview thay đổi trả `PRICE_CHANGED`, mã sai trả `COUPON_INVALID`, không tạo đơn dở.

Admin-only: `GET/POST coupons/`, `GET/PATCH/PUT coupons/{id}/`. Không DELETE hoặc đổi code. Chi tiết điều kiện, mẫu dữ liệu và lượt dùng: `../docs/COUPONS.md`.
