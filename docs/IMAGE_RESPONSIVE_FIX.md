# Sửa ảnh và bố cục co giãn — 13/10/2026

## Nguyên nhân và thay đổi

264 URL ảnh trong 278 sản phẩm nguồn: 12 URL trả HTTP 404, ảnh hưởng 24 dòng sản phẩm. Component trước đây thay ảnh lỗi bằng một placeholder chung, nên không còn hình đúng sản phẩm. Đã đối chiếu mẫu/mã và sửa đường dẫn hiển thị qua shared/product-image-overrides.json. Các URL nguồn, snapshot và file JSON gốc giữ nguyên.

Ảnh được tải trước vào shared/public/product-images, gồm 202 file nội dung khác nhau, dùng chung bởi 264 URL. Ưu tiên bản 600px của cùng tài nguyên CDN để hiển thị rõ hơn trên trang chi tiết. Manifest shared/product-images.json lưu URL, SHA256, kích thước; index nhỏ riêng được đưa vào bundle. Hai Vite app dùng chung publicDir và copy ảnh khi build. Trình duyệt ưu tiên ảnh local, nếu lỗi thử URL đã duyệt, sau đó placeholder có alt ghi rõ chưa có ảnh; đổi sản phẩm reset trạng thái lỗi, không lặp tải placeholder vô hạn.

Chạy lại việc tải ảnh tường minh từ root: `./.venv/Scripts/python.exe scripts/cache_product_images.py`. Lệnh không sửa database và chỉ tải từ các CDN được cho phép. Không tự tìm ảnh bằng từ khóa khi người dùng mở trang. URL thay thế và trang đối chiếu được ghi đầy đủ tại shared/product-image-overrides.json; các hình là ảnh sản phẩm từ nguồn, không phải ảnh AI.

Hai dòng nguồn cần lưu ý: Anker A2668 được hãng xác nhận là 735 GaNPrime 65W, trong khi tên dữ liệu ghi Prime 100W; ảnh dùng đúng mã A2668 và hiển thị ghi chú trên trang chi tiết ([Anker](https://www.anker.com/au/products/a2668?discount=WS242668EOFY&variant=45066704650543)). Aula AG75 Pro trên trang đối chiếu ghi kết nối có dây, khác tên nguồn ghi Tri-Mode; cũng có ghi chú, chưa tự đổi tên/thông số nguồn ([trang đối chiếu](https://cellphones.com.vn/ban-phim-co-co-day-aula-ag75-pro-xam.html)).

Bố cục trước dùng cột grid mặc định min-content, một số vùng flex không cho co nhỏ, bảng thông số/chuỗi dài có thể đẩy rộng trang. Đã dùng minmax(0, …), min-width:0, xuống dòng chuỗi dài, bảng thông số fixed layout, container theo chiều rộng với lề co giãn, cart/options chuyển hàng/cột khi hẹp. Catalog chuyển 1/2/3/4 cột theo kích thước; danh mục xuống dòng, chữ trên thẻ mobile dễ đọc hơn. Admin sidebar chuyển menu từ 1000px; bảng rộng cuộn trong vùng bảng thay vì kéo rộng trang.

## Kiểm chứng thực chạy

- 278/278 dòng nguồn có ảnh local; SHA256 và kích thước từng file khớp manifest.
- 404 yêu cầu HTTP (202 file × hai app) trả ảnh đúng nội dung, không trả HTML/404; ảnh cũng có trong hai thư mục dist sau build.
- 11 kiểm thử frontend PASS, gồm 3 ca mới cho fallback/reset ảnh và 1 ca kiểm tra toàn bộ tài nguyên. Hai app build PASS.
- Trình duyệt hiển thị đúng 6 ảnh Aula trước đây không tải được, không dùng placeholder.
- Catalog: iframe viewport 320, 390, 600, 750, 768, 820, 1024, 1440, 1920px; document.scrollWidth không vượt clientWidth, số cột tự đổi. Ở viewport390px có scrollbar dọc15px nên clientWidth375px, đây là kích thước CSS đo thực tế.
- Trang chủ, dashboard và bảng sản phẩm: 320, 390, 768, 1024, 1440, 1920px, không tràn document. Bảng sản phẩm có thể cuộn bên trong vùng bảng trên màn hình hẹp.
- Chi tiết bàn phím/laptop thông số dài, checkout có một hàng và POS: 320, 390, 768, 1024, 1440px. Checkout không submit; không tạo đơn/thu tiền cho việc kiểm tra bố cục. Đã gỡ sản phẩm thử khỏi giỏ.
- Bộ lọc catalog mở được ở390px. Admin kiểm thử dùng database riêng, cookie riêng, không tạo tài khoản thử trong database ứng dụng.

fe/responsive-check.html và admin/responsive-check.html là harness development cho việc kiểm tra viewport, không là entry build và không được copy vào dist. Thiết bị/zoom của trình duyệt thực tế khác vẫn nên được kiểm tra bổ sung; không coi iframe là chứng minh đã thử mọi trình duyệt.
