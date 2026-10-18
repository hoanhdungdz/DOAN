# Thiết kế ứng dụng khách hàng

React/Vite JavaScript/Tailwind, giao diện tiếng Việt. Routes /, /products, /products/:slug, /cart, /checkout, /orders, /orders/:id, /lookup, /login, /register, /forgot-password, /reset-password, /profile. Catalog API thật, VND bằng Intl.NumberFormat cho hiển thị; tổng tiền chính thức backend Decimal. Chi nhánh lựa chọn rõ, tồn theo chi nhánh.

Guest cart localStorage chỉ ID/số lượng; authenticated cart API. Login merge, giá/khả dụng refresh từ variants. Checkout yêu cầu chi nhánh/kho, tên/điện thoại, address nếu delivery. Pending có hủy; order owner API. OTP không lộ PII, local inbox bên backend filesystem. Ảnh error placeholder. Chat open/close/state-only, clear/logout xóa state; thông báo chưa bật AI. Không tạo OAuth giả.
