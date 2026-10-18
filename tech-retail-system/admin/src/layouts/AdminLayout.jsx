import React, { useState } from "react";
import { NavLink, Outlet, Navigate, useNavigate } from "react-router-dom";
import {
  LayoutDashboard,
  Package,
  Boxes,
  ShoppingBag,
  Store,
  Users,
  BarChart3,
  FileText,
  ShieldCheck,
  LogOut,
  Menu,
  X,
  ArrowUpRight,
  Search,
  ChevronRight,
} from "lucide-react";
import { useSession } from "../../../shared/session";
import { Loading, ErrorBox } from "../../../shared/ui";
const groups = [
  {
    label: "KHÔNG GIAN LÀM VIỆC",
    items: [
      ["/dashboard", "Tổng quan", LayoutDashboard, null],
      ["/pos", "Bán tại quầy", ShoppingBag, "manage_sales"],
      ["/orders", "Đơn hàng", FileText, "manage_sales"],
    ],
  },
  {
    label: "DỮ LIỆU & HÀNG HÓA",
    items: [
      ["/products", "Sản phẩm", Package, "manage_accounts"],
      ["/variants", "Biến thể & giá", Package, "manage_accounts"],
      ["/categories", "Danh mục", Package, "manage_accounts"],
      ["/brands", "Thương hiệu", Package, "manage_accounts"],
      ["/product-images", "Hình ảnh", Package, "manage_accounts"],
      ["/specifications", "Thông số", Package, "manage_accounts"],
      [
        "/specification-definitions",
        "Định nghĩa thông số",
        Package,
        "manage_accounts",
      ],
      ["/inventory", "Tồn kho", Boxes, null],
      ["/stock-documents", "Chứng từ kho", FileText, "manage_stock"],
      ["/stock-transfers", "Điều chuyển", Boxes, "manage_stock"],
      ["/movements", "Biến động kho", Boxes, "manage_stock"],
      ["/reservations", "Giữ chỗ", Boxes, "manage_stock"],
      ["/suppliers", "Nhà cung cấp", Store, "manage_stock"],
      ["/stores", "Chi nhánh", Store, "manage_accounts"],
      ["/warehouses", "Kho hàng", Store, "manage_accounts"],
    ],
  },
  {
    label: "BÁN HÀNG & CON NGƯỜI",
    items: [
      ["/payments", "Thu / hoàn tiền", FileText, "manage_payments"],
      ["/invoices", "Chứng từ bán hàng", FileText, "manage_sales"],
      ["/customers", "Khách hàng", Users, "manage_sales"],
      ["/employees", "Nhân viên", Users, "manage_people"],
      ["/reports", "Báo cáo", BarChart3, "view_reports"],
    ],
  },
  {
    label: "QUẢN TRỊ",
    items: [
      ["/users", "Tài khoản", Users, "manage_accounts"],
      ["/roles", "Vai trò & quyền", ShieldCheck, "manage_accounts"],
      ["/permissions", "Danh sách quyền", ShieldCheck, "manage_accounts"],
      ["/assignments", "Phân công chi nhánh", Store, "manage_accounts"],
      ["/audit-logs", "Nhật ký nghiệp vụ", FileText, "view_audit"],
    ],
  },
];
export default function AdminLayout() {
  const { user, loading, error, signOut } = useSession(),
    [open, setOpen] = useState(false),
    [search, setSearch] = useState(""),
    navigate = useNavigate();
  if (loading) return <Loading />;
  if (error)
    return (
      <main className="success panel">
        <ErrorBox error={error} />
        <button onClick={() => location.reload()}>Thử lại</button>
      </main>
    );
  if (!user) return <Navigate to="/login" replace />;
  if (!user.is_admin && !user.permissions.length)
    return (
      <main className="success panel">
        <h2>Tài khoản chưa có quyền nội bộ.</h2>
        <p>Quản trị viên cần gán vai trò và chi nhánh cho tài khoản.</p>
        <button onClick={signOut}>Đăng xuất</button>
      </main>
    );
  const can = (p) => !p || user.is_admin || user.permissions.includes(p);
  return (
    <div className="admin-shell">
      <aside className={`admin-sidebar ${open ? "open" : ""}`}>
        <div className="sidebar-brand">
          <NavLink to="/dashboard" className="wordmark">
            tech<span>retail</span>
            <i>®</i>
          </NavLink>
          <button
            className="sidebar-close"
            onClick={() => setOpen(false)}
            aria-label="Đóng menu"
          >
            <X size={18} />
          </button>
        </div>
        <div className="workspace-label">
          <i /> KHÔNG GIAN VẬN HÀNH <ChevronRight size={12} />
        </div>
        <nav>
          {groups.map(
            (g) =>
              g.items.some(([, , , p]) => can(p)) && (
                <section key={g.label}>
                  <small>{g.label}</small>
                  {g.items
                    .filter(([, , , p]) => can(p))
                    .map(([path, label, Icon]) => (
                      <NavLink
                        key={path}
                        to={path}
                        onClick={() => setOpen(false)}
                      >
                        <Icon size={16} />
                        <span>{label}</span>
                      </NavLink>
                    ))}
                </section>
              ),
          )}
        </nav>
        <div className="sidebar-bottom">
          <div className="workspace-avatar">
            {(user.full_name || user.email).slice(0, 1).toUpperCase()}
          </div>
          <div>
            <strong>{user.full_name || user.email}</strong>
            <small>
              {user.is_admin
                ? "Quản trị viên"
                : `${user.stores.length} chi nhánh được giao`}
            </small>
          </div>
          <button
            aria-label="Đăng xuất"
            onClick={async () => {
              await signOut();
              navigate("/login");
            }}
          >
            <LogOut size={16} />
          </button>
        </div>
      </aside>
      {open && (
        <div className="sidebar-overlay" onClick={() => setOpen(false)} />
      )}
      <div className="admin-main">
        <header className="admin-header">
          <div>
            <button
              className="mobile-menu"
              aria-label="Mở menu"
              onClick={() => setOpen(true)}
            >
              <Menu size={19} />
            </button>
            <span>Không gian vận hành</span>
            <ChevronRight size={13} />
            <strong>Tech Retail</strong>
          </div>
          <form
            onSubmit={(e) => {
              e.preventDefault();
              navigate("/orders?search=" + encodeURIComponent(search));
            }}
          >
            <Search size={15} />
            <input
              aria-label="Tìm mã đơn"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Tìm mã đơn…"
            />
          </form>
          <a href="http://localhost:5173" target="_blank" rel="noreferrer">
            Mở cửa hàng <ArrowUpRight size={14} />
          </a>
        </header>
        <main className="admin-body">
          <Outlet />
        </main>
        <footer className="admin-footer">
          TECH RETAIL / HỆ THỐNG PHỤC VỤ ĐỒ ÁN{" "}
          <span>Google · Facebook · Gemini: chưa tích hợp</span>
        </footer>
      </div>
    </div>
  );
}
