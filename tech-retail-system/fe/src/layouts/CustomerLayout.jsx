import React, { useState } from "react";
import { Link, NavLink, Outlet, useNavigate } from "react-router-dom";
import {
  Search,
  ShoppingBag,
  UserRound,
  ArrowUpRight,
  MapPin,
  MessageCircle,
  X,
  Send,
  RotateCcw,
} from "lucide-react";
import { useSession } from "../../../shared/session";
import { useCart } from "../features/cart/CartContext";
import { api } from "../../../shared/api";
export default function CustomerLayout() {
  const { user, signOut } = useSession(),
    { count } = useCart(),
    navigate = useNavigate(),
    [search, setSearch] = useState(""),
    [open, setOpen] = useState(false),
    [question, setQuestion] = useState(""),
    [messages, setMessages] = useState([]),
    [busy, setBusy] = useState(false);
  React.useEffect(() => {
    setMessages([]);
    setQuestion("");
  }, [user?.id]);
  async function ask(e) {
    e.preventDefault();
    if (!question.trim()) return;
    setBusy(true);
    const q = question;
    setQuestion("");
    try {
      const d = await api("ai/chat/", {
        method: "POST",
        body: { question: q, history: messages.slice(-6) },
      });
      setMessages((m) => [...m, { question: q, answer: d.answer }].slice(-10));
    } catch (e) {
      setMessages((m) =>
        [...m, { question: q, answer: e.message, error: true }].slice(-10),
      );
    } finally {
      setBusy(false);
    }
  }
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
      <button
        className="chat-toggle"
        onClick={() => setOpen(!open)}
        aria-label="Mở tư vấn AI"
      >
        {open ? <X size={21} /> : <MessageCircle size={21} />}
      </button>
      {open && (
        <section className="chat-panel">
          <header>
            <div>
              <strong>Tư vấn sản phẩm</strong>
              <small>AI chưa được bật</small>
            </div>
            <button
              onClick={() => {
                setMessages([]);
                setQuestion("");
              }}
              aria-label="Xóa hội thoại"
            >
              <RotateCcw size={16} />
            </button>
          </header>
          <div className="chat-content">
            <p className="notice">
              Chức năng tư vấn AI chưa được bật. Bạn có thể tìm thiết bị qua
              danh mục và bộ lọc.
            </p>
            {messages.map((m, i) => (
              <div key={i}>
                <p className="chat-question">{m.question}</p>
                <p className="subtle">{m.answer}</p>
              </div>
            ))}
            {busy && <p className="subtle">Đang xử lý…</p>}
          </div>
          <form onSubmit={ask}>
            <input
              aria-label="Câu hỏi tư vấn"
              maxLength={2000}
              placeholder="Nhập câu hỏi để kiểm tra trạng thái…"
              value={question}
              onChange={(e) => setQuestion(e.target.value)}
            />
            <button
              disabled={busy || !question.trim()}
              aria-label="Gửi câu hỏi"
            >
              <Send size={17} />
            </button>
          </form>
          <small className="fine">
            Hội thoại chỉ tồn tại trong trang hiện tại.
          </small>
        </section>
      )}
    </>
  );
}
