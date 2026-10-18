# Dự thảo chính sách bảo hành Tech Retail

Ngày đối chiếu: 18/10/2026. Cập nhật theo yêu cầu đồ án: **đã triển khai ô bảo hành và hộp chính sách theo từng biến thể trên trang sản phẩm**. Chính sách, thời gian và quầy dịch vụ là dữ liệu mô phỏng, không phải thông tin bảo hành hãng đã xác minh. Quy tắc triển khai được ghi tại [WARRANTY_DEMO_IMPLEMENTATION.md](WARRANTY_DEMO_IMPLEMENTATION.md); các nội dung cần xác minh trong bản nghiên cứu ban đầu bên dưới là thông tin đối chiếu nguồn.

Tài liệu dựa trên các nhóm hàng thực tế trong bộ nguồn của dự án, sau khi áp dụng danh sách hiệu chỉnh catalog. Tham khảo cách chia nội dung của [trang bảo hành CellphoneS](https://cellphones.com.vn/chinh-sach-bao-hanh): đổi trả, bảo hành tiêu chuẩn, bảo hành mở rộng và tìm điểm bảo hành theo hãng. Nội dung dưới đây được soạn riêng; không chuyển quyền lợi, mức phí hoặc mạng lưới dịch vụ của CellphoneS thành quyền lợi của Tech Retail.

## 1. Phạm vi và thông tin khách hàng cần thấy

Chính sách dự kiến áp dụng cho sản phẩm do Tech Retail bán và có thông tin giao dịch đối chiếu được. Mỗi sản phẩm cần công bố rõ: SKU, tình trạng, đơn vị chịu trách nhiệm bảo hành, thời hạn, mốc bắt đầu, bộ phận được bảo hành và các điều kiện riêng. Bảo hành hãng và bảo hành do cửa hàng cung cấp phải được ghi riêng nếu cùng tồn tại.

Thông tin phải được xác nhận khi bán và lưu cùng đơn hàng. Không suy ra quyền lợi chỉ từ tên hãng, nhãn “chính hãng”, tình trạng “mới”, hoặc một câu quảng cáo trong mô tả thu thập từ website khác.

## 2. Thời hạn đang có trong dữ liệu

Đây là **thống kê dữ liệu tham khảo, chưa xác minh là thời hạn hãng hoặc thời hạn cửa hàng cam kết**. Có 264 dòng hàng sau khi loại 14 dòng trùng đã được cách ly; không phải số lượng máy tồn kho. Không phải mọi sản phẩm trong cùng danh mục đều có một thời hạn chung.

| Nhóm hàng | Số dòng | Giá trị `warranty_months` hiện có |
|---|---:|---|
| Laptop | 50 | 50 dòng: 24 tháng |
| Điện thoại | 43 | 28 dòng: 6 tháng; 15 dòng: 12 tháng |
| Máy tính bảng | 52 | 45 dòng: 6 tháng; 7 dòng: 12 tháng |
| Máy tính để bàn / Mac mini | 13 | 13 dòng: 12 tháng |
| Màn hình PC | 37 | 9 dòng: 6 tháng; 28 dòng: 12 tháng |
| Âm thanh và đồng hồ thông minh | 50 | 3 dòng: 6 tháng; 47 dòng: 12 tháng |
| Gia dụng và Smarthome | 11 | 9 dòng: 12 tháng; 2 dòng: 24 tháng |
| Phụ kiện công nghệ | 8 | 1 dòng: 6 tháng; 7 dòng: 12 tháng |

Danh sách từng SKU nằm tại [WARRANTY_PRODUCT_REFERENCE.md](WARRANTY_PRODUCT_REFERENCE.md). Danh sách phản ánh bộ nguồn và file hiệu chỉnh, không phải kết quả kiểm tra thời hạn theo serial/IMEI hay truy vấn dữ liệu vận hành mới nhất.

**Mâu thuẫn cụ thể:** `PROD_0001` và `PROD_0002` có trường số tháng bằng 24, trong khi mô tả ghi 6–12 tháng. Chưa có căn cứ chọn bên nào đúng. Các laptop đã kích hoạt hoặc đã qua sử dụng vẫn đang có giá trị 24 tháng trong bộ nguồn; không được diễn giải thành “còn nguyên 24 tháng bảo hành hãng”.

## 3. Phân biệt theo tình trạng sản phẩm

| Tình trạng đang có | Nội dung cần áp dụng và công bố |
|---|---|
| Mới 100% (Chính hãng) | Xác nhận quyền lợi theo đúng model và thị trường phân phối; ghi riêng thời hạn thân máy, pin và phụ kiện nếu khác nhau. Không mặc định cả bộ có cùng thời hạn. |
| Đã kích hoạt | Kiểm tra ngày kích hoạt và ngày hết bảo hành hãng của thiết bị. Nếu cửa hàng bổ sung bảo hành, ghi rõ đơn vị thực hiện và khoảng thời gian bổ sung. Không tự tính lại bảo hành hãng từ ngày bán của cửa hàng. |
| Cũ đẹp / Like New | Lập ghi nhận ngoại hình, chức năng và phụ kiện khi bàn giao. Công bố phạm vi bảo hành cửa hàng và bảo hành hãng còn lại, nếu đã xác minh. “Like New” mô tả tình trạng, không tự tạo quyền lợi như máy mới. |
| Cũ trầy xước / xước cấn | Ghi nhận rõ vị trí và mức độ khuyết điểm đã thông báo. Khuyết điểm ngoại hình đã được chấp thuận không đồng nghĩa mọi lỗi chức năng phát sinh đều bị loại khỏi bảo hành. |
| Đã qua sử dụng | Áp dụng cho cả bốn sản phẩm gia dụng đã sửa nhãn tình trạng. Kiểm tra lịch sử sử dụng, bộ phụ kiện, pin và các bộ phận tiêu hao trước khi xác định quyền lợi. |
| Đổi bảo hành | Xác minh đây là thiết bị thay thế theo hồ sơ nào, còn thời hạn bao lâu và đơn vị nào chịu trách nhiệm. Nhãn tình trạng này không phải gói bảo hành mở rộng, không tự làm thời hạn bắt đầu lại. |

## 4. Phạm vi đánh giá bảo hành theo nhóm sản phẩm

Các nội dung sau là khung tiếp nhận và đánh giá đề xuất. Quyết định sửa chữa, thay thế linh kiện hoặc đổi thiết bị phải căn cứ lỗi được xác nhận và chính sách đã công bố cho SKU/thiết bị đó; không mặc định mọi lỗi đều được đổi mới.

### Laptop và máy tính để bàn

- Tiếp nhận lỗi phần cứng như không khởi động, lỗi bo mạch, RAM, SSD, GPU, màn hình, bàn phím tích hợp hoặc cổng kết nối để chẩn đoán nguyên nhân và phạm vi được bảo hành.
- Với Mac mini, đánh giá thân máy và phụ kiện thực tế được bán kèm; không coi màn hình, bàn phím hay chuột mua riêng là bộ phận của Mac mini.
- Pin, bộ sạc và linh kiện nâng cấp cần có phạm vi/thời hạn riêng nếu bên bảo hành quy định khác thân máy. Không lấy số tháng của thân máy áp dụng tự động cho mọi linh kiện.
- Phân biệt lỗi phần cứng với cấu hình hệ điều hành, ứng dụng, mã độc hoặc phần mềm không tương thích để thông báo hướng xử lý phù hợp.

### Điện thoại và máy tính bảng

- Tiếp nhận lỗi nguồn, màn hình/cảm ứng, camera, âm thanh, kết nối, sạc hoặc phần cứng khác để kiểm tra theo thiết bị cụ thể.
- Pin và phụ kiện có thể có điều kiện riêng. Không đặt ngưỡng dung lượng pin hoặc cam kết thay pin miễn phí khi chưa xác nhận chính sách tương ứng.
- Với hàng đã kích hoạt, hàng cũ và thiết bị đổi bảo hành, cần đối chiếu serial/IMEI và thời hạn thực tế; bộ nguồn hiện chưa có hồ sơ này.
- Việc đổi thiết bị, màu hoặc dung lượng khác chỉ thực hiện khi có phương án và sự đồng thuận của khách hàng; không tự thay đổi cấu hình.

### Màn hình PC

- Tiếp nhận lỗi hiển thị, nguồn, bảng mạch, cổng tín hiệu hoặc chức năng theo thông số sản phẩm.
- Điểm sáng, điểm chết, hở sáng và mức sai lệch hiển thị cần đánh giá theo chính sách hãng/model đã xác minh. Không dùng một số lượng điểm chết chung cho toàn bộ 37 dòng màn hình.
- Kiểm tra dây tín hiệu, nguồn phát, độ phân giải và tần số quét để phân biệt lỗi màn hình với cấu hình hoặc phụ kiện bên ngoài.

### Tai nghe, loa và đồng hồ thông minh

- Tai nghe/loa: đánh giá lỗi âm thanh, kết nối, điều khiển, sạc và hộp sạc nếu thuộc bộ sản phẩm đã bán.
- Đồng hồ: đánh giá màn hình, cảm ứng/nút bấm, sạc, kết nối và cảm biến theo chức năng của model.
- Pin, đệm tai, dây đeo, nút tai và phụ kiện khác phải được phân loại cụ thể. Hao mòn trong sử dụng và lỗi sản xuất cần được phân biệt bằng kiểm tra thực tế.
- Chỉ số kháng nước không tự bảo đảm mọi trường hợp tiếp xúc chất lỏng đều được bảo hành. Cần xác định nguyên nhân và điều kiện sử dụng theo model.

### Gia dụng và Smarthome

- Tivi: đánh giá tấm nền, nguồn, âm thanh, bảng mạch và kết nối. Bảo hành tại nhà chỉ công bố khi có đơn vị thực hiện, địa bàn và điều kiện đã xác nhận.
- Robot hút bụi: đánh giá động cơ, cảm biến, bo mạch, hệ thống sạc và trạm giặt/hút bụi nếu nằm trong cấu hình được bán.
- Pin, chổi, khăn lau, bộ lọc, túi bụi, dung dịch và các vật tư khác cần phân biệt lỗi khi giao hàng, lỗi sản xuất với hao mòn/tiêu hao; không tự áp dụng thời hạn thân máy hoặc loại bỏ mọi trường hợp.
- Khi tiếp nhận robot, ghi nhận tình trạng bình nước, khay bụi và phụ kiện; hướng dẫn đóng gói khô ráo trước khi vận chuyển.

### Phụ kiện công nghệ

- Bàn phím: đánh giá phím/switch, bảng mạch, đèn, cổng kết nối và chức năng có dây/không dây thực tế được xác nhận cho model.
- Sạc, cáp và phụ kiện điện: kiểm tra đầu nối, nguồn cấp, công suất tương thích và lỗi chức năng theo thông số đã xác minh.
- Không lấy nội dung tên sản phẩm thu thập được làm bằng chứng về cấu hình hoặc công suất khi đã có ghi chú dữ liệu mâu thuẫn trong dự án.

## 5. Điều kiện tiếp nhận và trường hợp xử lý có phí

Khách hàng cung cấp mã đơn, hóa đơn hoặc thông tin khác đủ để đối chiếu giao dịch. Không nên yêu cầu duy nhất bản hóa đơn giấy khi hệ thống đã xác minh được việc mua hàng. Với thiết bị có serial/IMEI, đối chiếu nhận dạng và tình trạng thực tế khi tiếp nhận.

Nếu kiểm tra xác định hư hỏng có nguyên nhân do va đập, chất lỏng, nguồn điện không phù hợp, can thiệp sửa chữa hoặc sử dụng sai hướng dẫn, cần thông báo kết quả và căn cứ liên quan đến lỗi yêu cầu xử lý. Không tự từ chối toàn bộ quyền lợi chỉ vì có vết xước hoặc dấu hiệu không liên quan đến lỗi.

Hết thời hạn hoặc nằm ngoài phạm vi miễn phí: cung cấp báo giá, nội dung công việc và chi phí vận chuyển phát sinh trước khi thực hiện. Khách hàng cần đồng ý với phương án có phí. Không tự thêm phí chẩn đoán, lưu kho hoặc phí xử lý nếu chưa thông báo và thỏa thuận.

## 6. Quy trình đề xuất

1. **Gửi yêu cầu:** khách cung cấp đơn hàng/SKU, mô tả triệu chứng và cách liên hệ; có thể bổ sung ảnh hoặc video để hỗ trợ phân loại.
2. **Tiếp nhận:** lập phiếu ghi nhận thiết bị, serial/IMEI nếu có, ngoại hình, phụ kiện, lỗi báo và thời điểm nhận. Gửi khách mã phiếu để theo dõi.
3. **Kiểm tra:** xác định tình trạng bảo hành và nguyên nhân; chuyển đơn vị có trách nhiệm khi cần. Thông báo thời gian dự kiến sau khi tiếp nhận và cập nhật khi thay đổi; chưa đặt một thời hạn chung khi chưa có căn cứ vận hành.
4. **Thống nhất phương án:** thông báo sửa chữa, thay linh kiện, đổi thiết bị hoặc phương án khác theo quyền lợi đã xác nhận. Báo giá và xin đồng ý trước nếu có phí.
5. **Bàn giao:** ghi rõ công việc đã làm, linh kiện/thiết bị thay thế, kết quả kiểm tra, thời hạn áp dụng sau xử lý và chi phí nếu có. Không tự làm mất hoặc khởi động lại thời hạn cũ khi chưa có quy định tương ứng.

Trước khi gửi máy, hướng dẫn khách sao lưu dữ liệu, tháo SIM/thẻ nhớ nếu không cần kiểm tra, và xử lý khóa tài khoản khi cần thiết. Không yêu cầu gửi mật khẩu tài khoản cá nhân. Khi cần xóa dữ liệu hoặc khôi phục cài đặt, thông báo và lấy sự đồng ý phù hợp; ghi nhận phạm vi truy cập dữ liệu phục vụ sửa chữa.

Địa điểm tiếp nhận, số điện thoại, giờ phục vụ, hỗ trợ tại nhà, đơn vị vận chuyển và bên chịu phí vận chuyển phải được bổ sung từ thông tin thật của Tech Retail. Không sử dụng địa chỉ hoặc tổng đài của CellphoneS làm thông tin của cửa hàng.

## 7. Đổi trả và bảo hành mở rộng

**Đổi trả cần phân biệt với sửa chữa bảo hành.** Trong phiên bản đồ án đã chọn quyền lợi đổi lỗi phần cứng trong 30 ngày theo quy tắc tại mục 8; hết hàng thì thống nhất chờ, đổi mẫu và chênh lệch hoặc hoàn số tiền thực trả của sản phẩm. Không áp dụng đổi do thay đổi nhu cầu khi máy không lỗi. Không sử dụng tỷ lệ khấu trừ của đơn vị tham khảo.

**Bảo hành mở rộng hiện chưa có trong code.** Chỉ công bố sau khi có gói cụ thể: giá, nhà cung cấp, thời gian, loại sự cố, giới hạn số lần/giá trị, phần chi trả của khách, quyền hủy gói và cách yêu cầu dịch vụ. Không trình bày nhãn “Đổi bảo hành” trong catalog như một gói đã mua.

## 8. Dữ liệu đã hoàn thiện cho phiên bản đồ án

Theo yêu cầu người dùng, dùng quy tắc mô phỏng sau để thay phần chờ hoàn thiện:

| Thông tin | Giá trị trong đồ án |
|---|---|
| Phiên bản, ngày hiệu lực | TR-BH-2026.01; 18/10/2026 |
| Thân máy | Số tháng `warranty_months` của biến thể đang chọn; không cố định 12 tháng |
| Đơn vị phụ trách | Hàng mới: chính hãng, Tech Retail nhận và phối hợp; các tình trạng khác: Tech Retail bảo hành |
| Mốc bắt đầu | Ngày nhận hàng hoặc nhận tại quầy; mô phỏng bảo đảm đủ thời hạn công bố |
| Pin nếu có | Hàng mới: tối đa 12 tháng; tình trạng khác: tối đa 6 tháng; không vượt thời hạn thân máy |
| Phụ kiện trong bộ bán | Tối đa 6 tháng, không vượt thời hạn thân máy; phụ kiện mua riêng theo trang riêng |
| Đổi lỗi | 30 ngày nếu xác nhận lỗi phần cứng được bảo hành; hết hàng thì thống nhất chờ, đổi mẫu và chênh lệch hoặc hoàn tiền sản phẩm |
| Phản hồi | Trong 1 ngày làm việc |
| Sửa chữa | Dự kiến 3–7 ngày làm việc, mốc xử lý 15 ngày; phát sinh kéo dài phải thông báo và thống nhất |
| Màn hình PC | Từ 3 điểm sáng hoặc 5 điểm tối được tiếp nhận đánh giá thay tấm nền; đây là tiêu chí mô phỏng |
| Tivi tại nhà | Phạm vi 15 km từ điểm tiếp nhận, mô phỏng |
| Vận chuyển | Hai chiều miễn phí cho lỗi được bảo hành; trường hợp khác báo phí trước |
| Sau thay linh kiện | Thời hạn còn lại hoặc 3 tháng, chọn dài hơn; đổi máy tiếp tục hạn ban đầu |
| Quầy tiếp nhận | Cầu Giấy — Hà Nội; Thanh Xuân — Hà Nội; Hoàng Diệu — Hải Phòng |
| Giờ tiếp nhận | 08:30–20:00 hằng ngày |
| Bảo hành mở rộng | Chưa bán gói có phí; không đồng nhất với tình trạng “Đổi bảo hành” |

Mô tả hiển thị có câu thời hạn dạng “bảo hành 6–12 tháng” được điều chỉnh theo biến thể đang chọn; bản JSON nguồn vẫn giữ nguyên để truy vết. Quy trình tiếp nhận trong chính sách là kịch bản đồ án, chưa phải module quản lý phiếu sửa chữa hoặc snapshot quyền lợi theo đơn.

## 9. Ghi chú triển khai dành cho dự án

Hiện có `ProductVariant.warranty_months`, ô bảo hành trên trang chi tiết và hộp chính sách có nội dung theo nhóm hàng/tình trạng/biến thể. `shared/warranty.js` là nơi cấu hình quy tắc mô phỏng; `fe/src/components/ProductWarranty.jsx` hiển thị nội dung. Chưa có backend quản lý phiếu bảo hành, serial/IMEI, tra cứu hoặc luồng sửa chữa.

Để quyền lợi theo đơn không đổi khi Admin sửa catalog, cần lưu snapshot chính sách và thời hạn cùng dòng hàng khi bán. Nếu quản lý theo thiết bị, bổ sung serial/IMEI, mốc bắt đầu/kết thúc, đơn vị phụ trách, nguồn xác minh và lịch sử tiếp nhận; không thay thế luồng bảo hành bằng trạng thái giao hàng hoặc hoàn tiền trước xuất kho.

Lần cập nhật này bổ sung giao diện và chính sách mô phỏng. Không sửa source JSON hoặc dữ liệu giao dịch; việc hiển thị chính sách không tự tạo phiếu bảo hành hay ghi snapshot mới vào đơn cũ.
