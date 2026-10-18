# Phân tích dữ liệu nguồn

Đọc toàn bộ `F:/đồ án/final_master_dataset.json` ngày 13/10/2026. Tên file thực tế khác `(1)` trong prompt nhưng dùng đúng file người dùng chỉ định. Bản sao phải có SHA256 `d063b0109c1ee9e29f7d79279b2deca5b0fbcf3f7afe4d425721013341c19964`.

278 dòng, mỗi dòng 16 trường, 7 danh mục, 33 brand sau trim; 3 chi nhánh; tổng tồn 2.824, từng dòng khớp tổng inventory. Cầu Giấy 956, Thanh Xuân 999, Hoàng Diệu 869. Các thống kê tham chiếu số lượng đều khớp.

| Danh mục nguồn | Số dòng | Tên giao diện |
|---|---:|---|
| Laptop | 50 | Laptop |
| Dien_thoai | 43 | Điện thoại |
| Gia_dung_Smarthome | 18 | Gia dụng & Smarthome |
| May_tinh_bang | 52 | Máy tính bảng |
| Phu_kien_Cong_nghe | 15 | Phụ kiện công nghệ |
| Man_hinh_PC | 50 | Màn hình PC |
| Am_thanh_Smartwatch | 50 | Âm thanh & Smartwatch |

ID/SKU không trùng. 13 giá trị slug trùng, tương ứng 13 URL nội bộ trùng: không được lấy slug làm identity. Slug nội bộ thêm source ID cho các bản ghi trùng, giữ original_slug/source snapshot. source_url có chuỗi rỗng lặp; không unique URL nguồn. Không có null; chuỗi rỗng được thống kê trong `data-analysis.json`. Price, warranty_months, total_stock đều int; inventory dict store->int; specs là string, image là một URL string, các trường khác string. Giá 490.000–109.990.000 VND. Một brand `Colorful ` ở PROD_0023 được trim thành Colorful. Không gộp Apple Chính hãng/Samsung Chính hãng với Apple/Samsung.

Tình trạng nguồn: Đã kích hoạt 38, Cũ đẹp (Like New) 62, Mới 100% (Chính hãng) 164, Cũ trầy xước 2, Đổi bảo hành 12. Snapshot giữ nguyên giá trị nguồn. Sau rà soát, bốn dòng tên/URL ghi Cũ được sửa condition vận hành thành Đã qua sử dụng; không suy đoán cấp ngoại hình. Specs tách các đoạn ` | ` và dấu `:` đầu tiên. Phần không hiểu giữ nguyên raw_specs; chuẩn hóa số chỉ bằng mẫu giá trị toàn phần với unit rõ ràng. Mỗi dòng vẫn có Product + Variant mặc định và source_snapshot đủ 16 trường.

Không có thời điểm kiểm kê trong file; đây là tồn đầu kỳ của nguồn đồ án, không đại diện tồn hiện tại của CellphoneS. Không kiểm chứng nội dung quảng cáo/bảo hành với bên ngoài, không tự sửa. Chi nhánh không có địa chỉ/điện thoại: để trống. File nguồn được giữ nguyên, import atomic/dry-run và chạy lại không reset tồn/giá.

14 bản ghi có source_url rỗng (không phải null). Giữ rỗng, không suy đoán URL. Không có trường thiếu hoặc khóa bổ sung trong file nguồn này. Có thể chạy lại báo cáo bằng `python scripts/analyze_dataset.py`; script đọc mọi bản ghi và không chỉnh sửa nguồn.

Rà soát ngữ nghĩa sau phản hồi người dùng: 14 dòng cuối lặp mẫu với các dòng trước đó nhưng có SKU/tồn khác; cách ly khỏi bán hàng, chưa cộng/gộp/xóa tồn. Có 7 cặp trong gia dụng, sau cách ly danh mục hiển thị 11 sản phẩm thay vì18. 13 Mac mini chuyển từ Màn hình PC sang Máy tính để bàn; danh mục vận hành có8 nhóm, catalog active264/278. Hai Dell Latitude cùng tên nhưng giá/nguồn khác vẫn giữ riêng. Chi tiết quyết định và cách phục hồi tại CATALOG_DATA_REVIEW.md.
