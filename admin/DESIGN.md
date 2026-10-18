# Thiết kế ứng dụng nhân viên

React/Vite JavaScript/Tailwind. Sidebar/header, tiếng Việt, responsive. Route: /login, /forgot-password, /reset-password; /dashboard; /products,/variants,/categories,/brands; /stores,/warehouses,/suppliers; /inventory,/movements,/stock-documents,/stock-transfers; /orders,/orders/:id,/pos,/payments,/invoices; /customers,/employees,/users,/roles,/assignments; /reports,/audit-logs. Menu lọc theo permissions, backend là nguồn quyết định.

Bảng GET API có search/filter/pagination/loading/error/empty. Form tạo/sửa validate fields, không generic edit balance/status. Action post/approve/dispatch/receive/thu/hoàn có xác nhận và phản hồi lỗi backend. POS dùng search variants và cart draft, chốt bằng finish. Invoice render snapshot và window.print. Không có doanh thu/data giả.
