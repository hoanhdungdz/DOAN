# Rà soát dữ liệu catalog — 13/10/2026

Ba lỗi người dùng chỉ ra có trong JSON nguồn; bước nhập ban đầu mới kiểm tra cấu trúc, chưa kiểm tra đủ ý nghĩa giữa tên/tình trạng/danh mục và các mẫu lặp.

| Vấn đề | Quyết định vận hành |
|---|---|
| 7 cặp gia dụng cùng mẫu, giá, ảnh nhưng khác SKU/tồn | Giữ bản có source_url hiển thị; 7 bản thiếu source_url ngừng bán chờ đối soát |
| 7 cặp phụ kiện có cùng vấn đề | Áp dụng cùng quy tắc; tổng14 Product is_active=false |
| PROD_0071–PROD_0074: tên/URL Cũ nhưng condition Mới | Đổi biến thể thành Đã qua sử dụng; chưa xác minh cấp ngoại hình nên không gán Like New |
| 13 Apple Mac mini gán Man_hinh_PC | Chuyển sang Máy tính để bàn, source_key May_tinh_de_ban |

Nhãn Mới ở góc ảnh là span của ProductCard lấy từ variant.condition, không phải chữ cần sửa trong file ảnh. Nhãn ở catalog, chi tiết, POS và đơn mới dùng condition đã sửa; snapshot đơn cũ được giữ nguyên.

Kết quả: Gia dụng18→11 sản phẩm active, Màn hình PC50→37, Máy tính để bàn13, Phụ kiện15→8. Tổng catalog active264, vẫn giữ đủ278 Product/Variant gốc. Không xóa/gộp SKU, giá, ảnh, raw snapshot, đơn hay số dư kho. Hai Dell Latitude 5420 cùng tên nhưng khác giá/nguồn không bị gộp.

## Thực hiện và kiểm soát

Các quyết định là danh sách đã đối chiếu tường minh ở be/data/catalog_corrections.json, không phải heuristic gộp mọi tên giống nhau. Service quality.py chỉ áp dụng cho master_dataset và source_id/metadata nguồn khớp. Với bản trùng, kiểm tra mẫu, giá, tình trạng, brand/category, chỉ một biến thể và chưa có thuộc tính phân biệt. Nếu dữ liệu vận hành đã đổi hoặc bản chuẩn không còn active, trả conflict để rà soát; không tự ghi đè. Mac mini đã được Admin đổi sang nhóm khác và condition đã sửa thủ công cũng không bị ghi đè.

Từ thư mục be:

```powershell
# Mặc định chỉ preview, rollback mọi thay đổi và audit.
../.venv/Scripts/python.exe manage.py review_catalog
# Áp dụng metadata với audit before/after và lý do.
../.venv/Scripts/python.exe manage.py review_catalog --apply
```

Import mới tự gọi service cho dòng được tạo/cập nhật nguồn, trong transaction import; dry-run rollback. Chạy lại nguồn giống hệt bỏ qua mọi dòng và giữ chỉnh sửa vận hành. API từ chối gán condition Mới cho tên ghi Cũ, hoặc đổi tên sang Cũ khi biến thể active vẫn là Mới. Có bộ lọc Đã qua sử dụng trên storefront.

Mỗi thay đổi ghi AuditLog action catalog.source_review, có source_id, canonical source_id (nếu là bản trùng), lý do, before/after. Danh sách thực áp dụng trong catalog-review-applied.json. Bản before đầy đủ riêng cho lần sửa này ở .runtime/catalog-before.json (không đưa vào frontend).

## Tồn bản trùng cần đối soát

194 đơn vị on_hand đang gắn với14 bản trùng, giữ nguyên để điều tra. Đây không phải194 đơn vị đã xác nhận là hàng vật lý riêng; không cộng vào bản chuẩn để tăng tồn. Báo cáo tồn vật lý hiện vẫn gồm các số dư này; hàng ngừng bán không được catalog/POS/cart/checkout mới chọn. Hàng trên đơn cũ, lịch sử và chứng từ vẫn giữ identity gốc.

Sau kiểm kê mới quyết định đây là hàng riêng hay nhập trùng. Nếu hàng riêng, Admin có thể đặt tên/thuộc tính phân biệt và bật lại Product; nếu nhập trùng, xử lý bằng chứng từ điều chỉnh có lý do theo quyền kho, không sửa balance trực tiếp. Admin có thể phục hồi category/condition/is_active từ audit hoặc bản before, nhưng cần kiểm tra các chỉnh sửa mới hơn trước khi phục hồi. Chưa thực hiện đối soát vật lý hay điều chỉnh194 đơn vị trong lần sửa này.

## Kiểm chứng

101 backend tests PASS trên MySQL, 11 frontend tests PASS, cả hai app build PASS. Các tests mới bao gồm dry-run, idempotency, giữ SKU/tồn/giá/snapshot, không nhầm các bản có khác biệt vận hành, API và checkout không bán bản đã cách ly. Đối chiếu database ứng dụng before/after xác nhận không đổi stock/ledger/price/source snapshot; reconcile834 balances không có sai lệch. Dữ liệu gốc và bản copy vẫn cùng SHA256.
