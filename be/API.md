# Thiết kế API v1

Base `/api/v1/`, JSON, session cookie HttpOnly; GET auth/csrf trả csrfToken, request POST/PATCH/DELETE gửi X-CSRFToken. GET auth/me trả user/permissions/scopes. Credentials include. Tất cả lỗi gồm code/message/fields/request_id; Decimal là chuỗi, datetime ISO8601 có timezone. Pagination page/page_size (max 100), response count/next/previous/results.

| Endpoint | Methods/actions | Quyền |
|---|---|---|
| auth/csrf,features | GET | Public |
| auth/register,login,forgot-password,reset-password | POST | Public + CSRF + throttle |
| auth/logout,change-password | POST | Đã đăng nhập |
| auth/me,profile | GET/PATCH | Chính mình |
| products,variants,categories,brands,stores | GET | Public active catalog |
| products,variants,categories,brands,stores,warehouses,suppliers | POST/PATCH | Admin catalog; kho theo scope |
| users,roles,permissions,assignments | GET/POST/PATCH | Admin |
| employees,customers | GET/PATCH | Nội bộ có scope; manager không đổi quyền |
| inventory,movements,reservations | GET | Nội bộ đúng scope; không PATCH balances |
| stock-documents | GET/POST/PATCH; POST /id/post,cancel | Quyền kho đúng chi nhánh |
| stock-transfers | GET/POST; POST /id/approve,dispatch,receive,cancel | Nguồn approve/dispatch; đích receive |
| carts | GET; POST merge; PUT items; DELETE item | Customer |
| orders | GET/POST; GET /id; POST /id/confirm,pack,ship,complete,cancel,finish | Public create ONLINE; owner read; staff scope |
| payments | GET/POST capture,refund | Sales/manager scope; khách không ghi tiền |
| order-lookup/request,verify | POST | Public + throttle + CSRF |
| order-lookup/result | GET | Session grant chỉ một đơn, 10 phút |
| invoices | GET | Owner hoặc nhân viên scope; tạo từ complete |
| reports/summary,inventory,export | GET | Permission + scope + dates |
| audit-logs | GET | Manager/Admin scope |
| ai/retrieval | GET | Public, filters catalog; không PII |
| ai/chat | POST | 503 AI_NOT_CONFIGURED |

Checkout: `{warehouse: ID, recipient_name, phone, address, fulfillment: DELIVERY|PICKUP, payment_method: COD|BANK_TRANSFER, items:[{variant:ID,quantity:1}]}` và header Idempotency-Key UUID. POS thêm channel IN_STORE, CASH hoặc BANK_TRANSFER (nhân viên có quyền); draft chưa giữ. Thao tác trạng thái có `{reason}`; thu/hoàn có `{order,reference}` và Idempotency-Key. Chứng từ `{warehouse,kind:IN|OUT|ADJUST,reason,supplier?,items:[{variant,quantity}]}`; ADJUST quantity là delta signed khác 0. Transfer `{source,destination,reason,items}`. OTP request `{code,phone}`, verify `{challenge,otp}`, không trả OTP.

Catalog filters: search,category,brand,store,price_min,price_max,condition,in_stock,spec; sort price/-price/name. Báo cáo start/end ISO date inclusive theo giờ Việt Nam, store filter không vượt scope. CSV chống formula injection. Validation/concurrency conflict 400/409, không quyền 403 hoặc hidden object 404, throttle 429, disabled 503.

`search` chỉ tên/SKU/thương hiệu; `spec` riêng cho text thông số. Không có parser câu hỏi tự nhiên tổng quát. Filters số chuẩn hóa dùng spec_definition + spec_min/spec_max, bắt buộc spec_unit để tránh so sánh nhầm GB/MB. Lọc price/condition/stock phải khớp cùng một variant, không gộp điều kiện từ các variant khác nhau. `internal=true` chỉ có hiệu lực khi là Admin; client không thể dùng nó để xem catalog ẩn.

POS có thể gửi thêm `customer: ID` để chọn khách hàng đã tồn tại: Admin toàn chuỗi, nhân viên chỉ khách có lịch sử đơn tại chi nhánh đang bán. Không tự liên kết theo số điện thoại; ONLINE không được ghi đè customer. Không capture tiền cho POS DRAFT qua payments; dùng action finish để thu tiền và xuất kho trong cùng transaction. Store/warehouse hỗ trợ scope=sales|stock|reports cho danh sách lựa chọn theo quyền. Images/spec metadata cho phép Admin DELETE; chứng từ và lịch sử giao dịch không xóa.

Cart GET/PUT/POST trả `{items:[{variant,quantity,details}],warnings:[]}`. Merge cộng số lượng có hạn mức, revalidate active variant và tồn hiện tại; bỏ dòng đã ngừng bán kèm cảnh báo, vượt tổng tồn được cảnh báo, không tự cắt số lượng hoặc giữ hàng. Checkout vẫn kiểm tra đủ hàng tại một kho. Báo cáo summary bổ sung monthly/by_store/by_channel; tồn là số dư hiện tại, không phải tồn tại thời điểm lịch sử cuối bộ lọc.

Catalog sau review nguồn có nhóm Máy tính để bàn và condition Đã qua sử dụng. Variant write từ chối condition bắt đầu bằng Mới khi tên product ghi Cũ; product write từ chối tên Cũ nếu vẫn có variant active mang condition Mới. Các Product lặp đã cách ly có is_active=false nên không xuất hiện ở API public/variants, không nhận checkout mới; Admin internal vẫn đọc và phục hồi được. Xem docs/CATALOG_DATA_REVIEW.md.

OpenAPI thực tế tại `openapi.yaml`, sinh bằng spectacular --validate, Swagger tại /api/docs/. Auth/lookup dùng action path với payload phụ thuộc action được mô tả bên trên. Throttle mặc định auth/lookup 10/phút và giới hạn API theo user/IP; cache local theo tiến trình trong cấu hình development hiện tại, OTP/reset cooldown và attempts được lưu MySQL. Khi triển khai nhiều worker cần cache/throttle dùng chung (có thể database cache), không coi cấu hình development là rate limit toàn cụm.
