import React, { useState } from "react";
import { Link, Outlet, useNavigate } from "react-router-dom";
import { Search, ShoppingBag, UserRound, ArrowUpRight } from "lucide-react";
import { useSession } from "../../../shared/session";
import { useCart } from "../features/cart/CartContext";
import ProductChat from "../components/ProductChat";
export default function CustomerLayout() {
  const { user, signOut } = useSession(),
    { count } = useCart(),
    navigate = useNavigate(),
    [search, setSearch] = useState("");
  return (
    <>
      <div className="announcement">
        <span>CÔNG NGHỆ CHO MỖI NGÀY</span>
        <Link to="/orders">
          Đơn hàng của tôi <ArrowUpRight size={12} />
        </Link>
      </div>
      <header className="customer-header">
        <div className="header-inner">
          <Link to="/" className="wordmark">
            tech<span>retail</span>
            <i>®</i>
          </Link>
          <form
            className="header-search"
            onSubmit={(e) => {
              e.preventDefault();
              navigate("/products?search=" + encodeURIComponent(search));
            }}
          >
            <Search size={17} />
            <input
              aria-label="Tìm sản phẩm"
              placeholder="Bạn đang tìm thiết bị gì?"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
            />
            <kbd>↵</kbd>
          </form>
          <nav>
            <Link to="/products">Khám phá</Link>
            {user ? (
              <>
                <Link to="/profile" aria-label="Tài khoản">
                  <UserRound size={20} />
                </Link>
                <button
                  className="text-button"
                  onClick={async () => {
                    await signOut();
                    navigate("/");
                  }}
                >
                  Đăng xuất
                </button>
              </>
            ) : (
              <Link to="/login" className="account-link">
                <UserRound size={19} />
                <span>Đăng nhập</span>
              </Link>
            )}
            <Link
              to="/cart"
              className="cart-icon"
              aria-label={`Giỏ hàng ${count} sản phẩm`}
            >
              <ShoppingBag size={21} />
              {count > 0 && <b>{count}</b>}
            </Link>
          </nav>
        </div>
      </header>
      <div className="customer-body">
        <Outlet />
      </div>
      <footer className="customer-footer">
        <div>
          <Link to="/" className="wordmark">
            tech<span>retail</span>
            <i>®</i>
          </Link>
          <p>Thiết bị tốt. Những khả năng mới.</p>
        </div>
        <div>
          <small>KHÁM PHÁ</small>
          <Link to="/products">Tất cả sản phẩm</Link>
          <Link to="/orders">Đơn hàng của bạn</Link>
        </div>
        <div>
          <small>HỖ TRỢ</small>
          <Link to="/orders">Theo dõi đơn hàng của tôi</Link>
          <Link to="/profile">Tài khoản</Link>
        </div>
        <div className="footer-bottom">
          © 2026 Tech Retail <span>Được xây dựng cho trải nghiệm rõ ràng.</span>
        </div>
      </footer>
      <ProductChat />
    </>
  );
}
