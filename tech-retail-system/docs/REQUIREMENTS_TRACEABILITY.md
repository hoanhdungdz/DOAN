# Truy vết yêu cầu

Mã F là mã tạm vì chưa có SRS/ID UC văn bản được xác nhận. F01–F19 đã có model/service/API và giao diện tương ứng, đã build hai frontend và chạy kiểm thử tự động trên MySQL. Cột kiểm thử là nhóm kiểm chứng tự động, không có nghĩa toàn bộ màn hình đã được nghiệm thu thủ công. Kết quả và giới hạn tại TEST_RESULTS.md.

| Mã | Chức năng | Màn hình | API / service | Entity | Kiểm thử | Trạng thái |
|---|---|---|---|---|---|---|
| F01 | Auth/reset/profile | Hai app Auth, account | auth/* | User,Customer | auth/CSRF/reset | Đã triển khai; kiểm thử tự động PASS |
| F02 | RBAC/nhân viên | Admin users/roles/employees | users,roles,employees | Group,Assignment | scope/escalation | Đã triển khai; kiểm thử tự động PASS |
| F03 | Catalog | Catalog/detail; Admin catalog | products/variants/categories/brands | Product,Variant,Spec,Image | filters/validation | Đã triển khai; kiểm thử tự động PASS |
| F04 | Nguồn/import/rà soát | Command; Admin catalog/audit | import_products,review_catalog | SourceSnapshot,Movement,AuditLog | full/dry-run/reimport/quality | Đã triển khai; kiểm thử tự động PASS |
| F05 | Chi nhánh/kho | Admin stores/warehouses | stores/warehouses | Store,Warehouse | scope | Đã triển khai; kiểm thử tự động PASS |
| F06 | Nhà cung cấp/chứng từ | Admin suppliers/stock-documents | post_document | Supplier,StockDocument | post once/rollback | Đã triển khai; kiểm thử tự động PASS |
| F07 | Tồn và lịch sử | Admin inventory/movements | reconcile_inventory | Balance,Movement,Reservation | constraints/reconciliation | Đã triển khai; kiểm thử tự động PASS |
| F08 | Điều chuyển | Admin transfers | transition_transfer | Transfer,Reservation | approve/dispatch/receive | Đã triển khai; kiểm thử tự động PASS |
| F09 | Cart/checkout | FE cart/checkout | carts/orders | Cart,Order | merge/server price/race | Đã triển khai; kiểm thử tự động PASS |
| F10 | POS | Admin pos | finish_pos | Order,Payment,Invoice | atomic/idempotency | Đã triển khai; kiểm thử tự động PASS |
| F11 | Trạng thái đơn | Hai app order detail | transition_order | OrderHistory | expire/cancel/ship | Đã triển khai; kiểm thử tự động PASS |
| F12 | Thanh toán/hoàn | Admin payments | record_payment | PaymentTransaction | duplicate/refund | Đã triển khai; kiểm thử tự động PASS |
| F13 | Tra cứu OTP | FE lookup | order-lookup/* | OTPChallenge | expiry/reuse/attempts | Đã triển khai; kiểm thử tự động PASS |
| F14 | In chứng từ | Admin invoice | invoices | Invoice | no side effects | Đã triển khai; kiểm thử tự động PASS |
| F15 | Khách/lịch sử | FE profile/Admin customers | customers/orders | Customer | ownership/PII | Đã triển khai; kiểm thử tự động PASS |
| F16 | Báo cáo/CSV | Admin reports | reports | Orders/Payments/Balance | dates/scope/CSV | Đã triển khai; kiểm thử tự động PASS |
| F17 | Audit | Admin audit | audit-logs | AuditLog | scope/no secrets | Đã triển khai; kiểm thử tự động PASS |
| F18 | Retrieval | Catalog; AI widget | ai/retrieval | Variant/Balance | DB results | Đã triển khai; kiểm thử tự động PASS |
| F19 | Flags/AI interface | AI disabled | features/ai/chat | Không chat tables | 503/interface | API/UI disabled đã kiểm thử; provider DEFERRED |

OAuth/Gemini DEFERRED; F19 chỉ hoàn tất giao diện và phản hồi khi tích hợp tắt, chưa có provider AI thật. Cổng thanh toán ngoài OUT_OF_SCOPE. Luồng UI đã kiểm tra trực tiếp: đăng nhập Admin, dashboard, chứng từ nhập/ghi sổ, guest checkout, xử lý đơn/thu COD/hoàn tất/xem invoice và tìm iPhone. Các màn hình còn lại có source, build và kiểm thử API; cần UAT theo TEST_PLAN.md trước khi vận hành.
