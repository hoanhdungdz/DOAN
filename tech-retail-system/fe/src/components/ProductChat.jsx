import React, { useEffect, useRef, useState } from "react";
import { Link, useLocation } from "react-router-dom";
import { MessageCircle, X, Send, RotateCcw, Sparkles } from "lucide-react";
import { api, money, dateTime } from "../../../shared/api";
import { ProductImage } from "../../../shared/ui";
import { useSession } from "../../../shared/session";
import "./ProductChat.css";

const examples = [
  "Laptop dưới 20 triệu còn hàng ở Cầu Giấy",
  "Chính sách đổi lỗi như thế nào?",
];

export default function ProductChat() {
  const { user } = useSession(),
    location = useLocation();
  const identity = user?.id ?? null;
  const currentIdentity = useRef(identity);
  currentIdentity.current = identity;
  const [open, setOpen] = useState(false),
    [question, setQuestion] = useState("");
  const [messages, setMessages] = useState([]),
    [busy, setBusy] = useState(false);
  const [owner, setOwner] = useState(identity);
  const [feature, setFeature] = useState({
    loading: true,
    enabled: false,
    error: "",
  });
  const generation = useRef(0),
    flight = useRef(null),
    bottom = useRef(null);
  function clear() {
    generation.current++;
    flight.current?.abort();
    flight.current = null;
    setBusy(false);
    setMessages([]);
    setQuestion("");
  }
  useEffect(() => {
    clear();
    setOwner(identity);
  }, [identity]);
  useEffect(
    () => () => {
      generation.current++;
      flight.current?.abort();
    },
    [],
  );
  useEffect(() => {
    if (!open) return;
    let live = true;
    setFeature({ loading: true, enabled: false, error: "" });
    api("features/")
      .then((data) => {
        if (live)
          setFeature({
            loading: false,
            enabled: data.gemini === true,
            error: "",
          });
      })
      .catch(() => {
        if (live)
          setFeature({
            loading: false,
            enabled: false,
            error:
              "Chưa kết nối được trợ lý. Bạn hãy đóng và mở lại khung chat để thử lại.",
          });
      });
    return () => {
      live = false;
    };
  }, [open]);
  useEffect(() => {
    bottom.current?.scrollIntoView?.({ block: "nearest" });
  }, [messages, busy, open]);
  async function ask(text) {
    const q = text.trim();
    if (!q || q.length > 2000 || flight.current || !feature.enabled) return;
    const controller = new AbortController(),
      version = ++generation.current,
      account = identity;
    flight.current = controller;
    const history = messages
      .filter(
        (item) => !item.error && !item.pending && item.mode !== "guidance",
      )
      .slice(-3)
      .map((item) => ({ question: item.question }));
    setQuestion("");
    setBusy(true);
    setMessages((items) =>
      [...items, { id: version, question: q, pending: true }].slice(-10),
    );
    const slug =
      location.pathname.match(/^\/products\/([a-zA-Z0-9_-]+)\/?$/)?.[1] || "";
    try {
      const data = await api("ai/chat/", {
        method: "POST",
        signal: controller.signal,
        body: { question: q, history, product_slug: slug },
      });
      if (version === generation.current && account === currentIdentity.current)
        setMessages((items) =>
          items.map((item) =>
            item.id === version ? { ...data, id: version, question: q } : item,
          ),
        );
    } catch (error) {
      if (
        version === generation.current &&
        account === currentIdentity.current &&
        error.name !== "AbortError"
      )
        setMessages((items) =>
          items.map((item) =>
            item.id === version
              ? { id: version, question: q, answer: error.message, error: true }
              : item,
          ),
        );
    } finally {
      if (version === generation.current) {
        flight.current = null;
        setBusy(false);
      }
    }
  }
  const visibleMessages = owner === identity ? messages : [];
  return (
    <>
      <button
        className="chat-toggle"
        onClick={() => setOpen(!open)}
        aria-label={open ? "Đóng tư vấn AI" : "Mở tư vấn AI"}
        aria-expanded={open}
        aria-controls="product-chat"
      >
        {open ? <X size={21} /> : <MessageCircle size={21} />}
      </button>
      {open && (
        <section
          id="product-chat"
          className="chat-panel rag-chat"
          role="dialog"
          aria-label="Trợ lý TechRetail"
        >
          <header>
            <div>
              <strong>
                <Sparkles size={16} /> Trợ lý TechRetail
              </strong>
              <small>
                {feature.loading
                  ? "Đang kết nối…"
                  : feature.enabled
                    ? "Tư vấn từ sản phẩm & chính sách cửa hàng"
                    : "Tư vấn đang tạm nghỉ"}
              </small>
            </div>
            <button type="button" onClick={clear} aria-label="Xóa hội thoại">
              <RotateCcw size={16} />
            </button>
          </header>
          <div className="chat-content" aria-live="polite" aria-busy={busy}>
            {!visibleMessages.length && (
              <div className="chat-welcome">
                <p>Chào bạn! Bạn đang tìm thiết bị cho nhu cầu nào?</p>
                <p className="fine">
                  Tôi có thể gợi ý sản phẩm, đọc thông số và giải thích chính
                  sách TechRetail.
                </p>
                <div className="chat-examples">
                  {examples.map((text) => (
                    <button
                      type="button"
                      key={text}
                      disabled={!feature.enabled || busy}
                      onClick={() => ask(text)}
                    >
                      {text}
                    </button>
                  ))}
                </div>
              </div>
            )}
            {(feature.error || (!feature.loading && !feature.enabled)) && (
              <p className="notice" role="status">
                {feature.error ||
                  "Trợ lý chưa được bật. Bạn vẫn có thể tìm sản phẩm bằng danh mục và bộ lọc."}
              </p>
            )}
            {visibleMessages.map((message) => (
              <article className="chat-exchange" key={message.id}>
                <p className="chat-question">{message.question}</p>
                {message.pending ? (
                  <p role="status" className="fine">
                    Đang tìm dữ liệu và soạn câu trả lời…
                  </p>
                ) : (
                  <>
                    {message.mode === "catalog" && (
                      <p className="fine" role="status">
                        Tra cứu danh mục · Tư vấn AI tạm ngừng
                      </p>
                    )}
                    <p
                      className={
                        message.error ? "chat-answer chat-error" : "chat-answer"
                      }
                      role={message.error ? "alert" : undefined}
                    >
                      {message.answer}
                    </p>
                    {message.error && (
                      <button
                        className="chat-retry"
                        type="button"
                        disabled={busy}
                        onClick={() => ask(message.question)}
                      >
                        Thử lại câu hỏi
                      </button>
                    )}
                    {message.products?.map(
                      (product) =>
                        /^\/products\/[a-zA-Z0-9_-]+$/.test(product.path) && (
                          <Link
                            className="chat-product"
                            key={product.id}
                            to={product.path}
                            onClick={() => setOpen(false)}
                          >
                            <ProductImage
                              src={product.image}
                              alt={product.name}
                              loading="lazy"
                            />
                            <div>
                              <strong>{product.name}</strong>
                              <span className="chat-product-price">
                                {money(product.price)}
                              </span>
                              <small>
                                {product.condition} ·{" "}
                                {product.warranty_months > 0
                                  ? `Bảo hành ${product.warranty_months} tháng`
                                  : "Không áp dụng bảo hành"}
                              </small>
                              <small>
                                {product.stock?.length
                                  ? product.stock
                                      .map(
                                        (stock) =>
                                          `${stock.store_name}: ${stock.available > 0 ? "có hàng" : "hết hàng"}`,
                                      )
                                      .join(" · ")
                                  : "Chưa có thông tin tồn kho"}
                              </small>
                              <span className="chat-product-link">
                                Xem sản phẩm →
                              </span>
                            </div>
                          </Link>
                        ),
                    )}
                    {message.sources?.length > 0 && (
                      <details className="chat-sources">
                        <summary>
                          Nguồn tham khảo ({message.sources.length})
                        </summary>
                        {message.sources.map((source) => (
                          <div key={source.id}>
                            <strong>{source.title}</strong>
                            <p>{source.excerpt}</p>
                          </div>
                        ))}
                      </details>
                    )}
                    {message.actions
                      ?.filter((action) =>
                        ["/orders", "/profile", "/products"].includes(
                          action.path,
                        ),
                      )
                      .map((action) => (
                        <Link
                          className="chat-action"
                          key={action.path}
                          to={action.path}
                          onClick={() => setOpen(false)}
                        >
                          {action.label} →
                        </Link>
                      ))}
                    {message.products?.length > 0 && (
                      <small className="fine">
                        Giá và tồn kho cập nhật lúc{" "}
                        {dateTime(message.checked_at)}; được kiểm tra lại khi
                        đặt hàng.
                      </small>
                    )}
                  </>
                )}
              </article>
            ))}
            <div ref={bottom} />
          </div>
          <form
            onSubmit={(event) => {
              event.preventDefault();
              ask(question);
            }}
          >
            <input
              aria-label="Câu hỏi tư vấn"
              maxLength={2000}
              placeholder="Nhu cầu, ngân sách hoặc câu hỏi của bạn…"
              value={question}
              disabled={busy || !feature.enabled}
              onChange={(event) => setQuestion(event.target.value)}
            />
            <button
              type="submit"
              disabled={busy || !question.trim() || !feature.enabled}
              aria-label="Gửi câu hỏi"
            >
              <Send size={17} />
            </button>
          </form>
          <small className="fine">
            AI có thể nhầm. Không gửi mật khẩu, OTP hoặc thông tin ngân hàng.
            Hội thoại chỉ lưu trong trang này.
          </small>
        </section>
      )}
    </>
  );
}
