# DOAN — Tech Retail

Đồ án tốt nghiệp: hệ thống quản lý chuỗi bán lẻ công nghệ.

## Cấu trúc repository

```text
DOAN/
├── tech-retail-system/   # Source code, dữ liệu catalog, kiểm thử và tài liệu
│   ├── fe/              # Website khách hàng — React/Vite
│   ├── admin/           # Website quản trị và nhân viên — React/Vite
│   ├── be/              # Backend — Django REST/MySQL
│   ├── shared/          # Thành phần dùng chung và ảnh sản phẩm
│   ├── scripts/
│   ├── tests/
│   └── docs/
├── Database Diagram/
├── Sequence Diagram/
├── class/
└── uc/
```

## Mở và chạy dự án

```powershell
git clone https://github.com/hoanhdungdz/DOAN.git
cd DOAN/tech-retail-system
```

Thực hiện các bước cài đặt, cấu hình MySQL, tạo file `.env` riêng và tạo tài khoản quản trị theo [hướng dẫn của ứng dụng](tech-retail-system/README.md). Các lệnh chạy và kiểm thử ứng dụng được thực hiện từ thư mục `tech-retail-system`, hoặc thư mục `be` khi hướng dẫn yêu cầu.

- [Kiến trúc hệ thống](tech-retail-system/ARCHITECTURE.md)
- [Quy tắc nghiệp vụ](tech-retail-system/docs/BUSINESS_RULES.md)
- [Kết quả kiểm thử](tech-retail-system/docs/TEST_RESULTS.md)
- [Chính sách bảo hành mô phỏng](tech-retail-system/docs/WARRANTY_DEMO_IMPLEMENTATION.md)

Đây là phiên bản phục vụ đồ án. File cấu hình bí mật, dữ liệu runtime, môi trường Python và thư viện Node được giữ ngoài Git; các mẫu cấu hình `.env.example` nằm trong thư mục ứng dụng.
