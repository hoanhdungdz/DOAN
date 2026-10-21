import React, { useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import {
  BadgeCheck,
  Camera,
  Headphones,
  MessageCircle,
  Search,
  Send,
  ShieldCheck,
  Star,
  ThumbsUp,
  Flag,
  X,
} from "lucide-react";
import { api, dateTime, errorText } from "../../../shared/api";
import { useSession } from "../../../shared/session";
import { ErrorBox, Field, Loading, Pager } from "../../../shared/ui";
import useRemote from "../../../shared/useRemote";
import "./ProductCommunity.css";

const statusLabel = { PENDING: "Đang chờ duyệt", HIDDEN: "Đã ẩn" };
export function Stars({ value = 0, size = 17 }) {
  return (
    <span className="community-stars" aria-label={`${value} trên 5 sao`}>
      {[1, 2, 3, 4, 5].map((n) => (
        <Star
          key={n}
          size={size}
          fill={n <= Math.round(value) ? "currentColor" : "none"}
        />
      ))}
    </span>
  );
}

export default function ProductCommunity(props) {
  const { user } = useSession();
  return (
    <CommunityView
      key={`${props.product.id}:${user?.id || "guest"}`}
      {...props}
      user={user}
    />
  );
}

function CommunityView({ product, user, children }) {
  const [tab, setTab] = useState("REVIEW"),
    [rating, setRating] = useState(""),
    [photos, setPhotos] = useState(false),
    [sort, setSort] = useState("newest"),
    [search, setSearch] = useState(""),
    [answered, setAnswered] = useState(""),
    [page, setPage] = useState(1),
    [revision, setRevision] = useState(0);
  const kind = tab === "DETAILS" ? "REVIEW" : tab;
  const params = new URLSearchParams({
    kind,
    page,
    rating: kind === "REVIEW" ? rating : "",
    photos: kind === "REVIEW" ? String(photos) : "false",
    sort,
    search: kind === "QUESTION" ? search : "",
    answered: kind === "QUESTION" ? answered : "",
  });
  const remote = useRemote(
      `products/${product.slug}/feedback/?${params}`,
      revision,
    ),
    summary = remote.data?.summary,
    viewer = remote.data?.viewer;
  const refresh = () => setRevision((n) => n + 1);
  const changeTab = (next) => {
    setTab(next);
    setPage(1);
  };
  const filter = (setter) => (value) => {
    setter(value);
    setPage(1);
  };
  return (
    <section
      className="product-community"
      aria-label="Đánh giá và hỏi đáp sản phẩm"
    >
      <div
        className="community-tabs"
        role="tablist"
        aria-label="Thông tin sản phẩm"
      >
        {[
          ["DETAILS", "Thông số"],
          ["REVIEW", "Đánh giá"],
          ["QUESTION", "Hỏi đáp"],
        ].map(([key, label]) => (
          <button
            type="button"
            key={key}
            role="tab"
            id={`community-tab-${key}`}
            aria-controls="community-content"
            aria-selected={tab === key}
            tabIndex={tab === key ? 0 : -1}
            onKeyDown={(e) => {
              const tabs = ["DETAILS", "REVIEW", "QUESTION"];
              const index = tabs.indexOf(tab);
              const next =
                e.key === "ArrowRight"
                  ? tabs[(index + 1) % 3]
                  : e.key === "ArrowLeft"
                    ? tabs[(index + 2) % 3]
                    : e.key === "Home"
                      ? tabs[0]
                      : e.key === "End"
                        ? tabs[2]
                        : null;
              if (next) {
                e.preventDefault();
                changeTab(next);
                document.getElementById(`community-tab-${next}`)?.focus();
              }
            }}
            onClick={() => changeTab(key)}
          >
            {label}
            {key !== "DETAILS" && summary
              ? ` (${key === "REVIEW" ? summary.count : summary.questions})`
              : ""}
          </button>
        ))}
      </div>
      <div
        id="community-content"
        role="tabpanel"
        aria-labelledby={`community-tab-${tab}`}
      >
        {tab === "DETAILS" ? (
          children
        ) : (
          <div
            className={`community-grid ${kind === "QUESTION" ? "questions" : ""}`}
          >
            <section className="panel community-list">
              <h2>
                {kind === "REVIEW" ? "Đánh giá sản phẩm" : "Hỏi đáp sản phẩm"}
              </h2>
              {kind === "REVIEW" ? (
                <div className="rating-overview">
                  <div>
                    <strong>
                      {summary?.average == null
                        ? "—"
                        : String(summary.average).replace(".", ",")}
                      <small>/5</small>
                    </strong>
                    <Stars value={summary?.average || 0} size={24} />
                    <p className="fine">{summary?.count || 0} đánh giá</p>
                  </div>
                  <div className="rating-distribution">
                    {[5, 4, 3, 2, 1].map((n) => (
                      <div key={n}>
                        <span>{n} sao</span>
                        <span className="rating-track">
                          <i
                            style={{
                              width: `${summary?.count ? (100 * (summary.distribution[n] || 0)) / summary.count : 0}%`,
                            }}
                          />
                        </span>
                        <span>{summary?.distribution[n] || 0}</span>
                      </div>
                    ))}
                  </div>
                </div>
              ) : (
                <>
                  <p className="subtle">
                    Bạn có thắc mắc? TechRetail sẵn sàng hỗ trợ.
                  </p>
                  <FeedbackForm
                    key="question"
                    kind="QUESTION"
                    product={product}
                    user={user}
                    viewer={viewer}
                    onSent={refresh}
                    loading={remote.loading}
                  />
                </>
              )}
              <div className="community-filters">
                {kind === "REVIEW" ? (
                  <>
                    <select
                      aria-label="Lọc số sao"
                      value={rating}
                      onChange={(e) => filter(setRating)(e.target.value)}
                    >
                      <option value="">Tất cả số sao</option>
                      {[5, 4, 3, 2, 1].map((n) => (
                        <option key={n} value={n}>
                          {n} sao
                        </option>
                      ))}
                    </select>
                    <button
                      type="button"
                      className={photos ? "selected" : ""}
                      aria-pressed={photos}
                      onClick={() => filter(setPhotos)(!photos)}
                    >
                      Có hình ảnh
                    </button>
                    <select
                      aria-label="Sắp xếp đánh giá"
                      value={sort}
                      onChange={(e) => filter(setSort)(e.target.value)}
                    >
                      <option value="newest">Mới nhất</option>
                      <option value="helpful">Hữu ích nhất</option>
                    </select>
                  </>
                ) : (
                  <>
                    <label className="community-search">
                      <Search size={17} />
                      <input
                        aria-label="Tìm trong câu hỏi"
                        placeholder="Tìm trong câu hỏi"
                        value={search}
                        onChange={(e) => filter(setSearch)(e.target.value)}
                      />
                    </label>
                    <select
                      aria-label="Lọc câu trả lời"
                      value={answered}
                      onChange={(e) => filter(setAnswered)(e.target.value)}
                    >
                      <option value="">Tất cả câu hỏi</option>
                      <option value="true">Đã trả lời</option>
                      <option value="false">Chưa trả lời</option>
                    </select>
                  </>
                )}
              </div>
              <ErrorBox error={remote.error} />
              {remote.loading ? (
                <Loading />
              ) : (
                remote.data &&
                (remote.data.results.length ? (
                  <>
                    {remote.data.results.map((item) => (
                      <FeedbackThread
                        key={item.id}
                        item={item}
                        user={user}
                        onChange={refresh}
                      />
                    ))}
                    {remote.data.count > 20 && (
                      <Pager
                        page={page}
                        setPage={setPage}
                        count={remote.data.count}
                      />
                    )}
                  </>
                ) : (
                  <div className="community-empty">
                    <MessageCircle size={32} />
                    <h3>
                      {kind === "REVIEW"
                        ? "Chưa có đánh giá phù hợp"
                        : "Chưa có câu hỏi phù hợp"}
                    </h3>
                    <p className="subtle">
                      {kind === "REVIEW"
                        ? "Chia sẻ trải nghiệm của bạn sau khi nhận hàng."
                        : "Hãy gửi câu hỏi đầu tiên về sản phẩm này."}
                    </p>
                  </div>
                ))
              )}
              {remote.error && (
                <button onClick={refresh}>Tải lại nội dung</button>
              )}
            </section>
            <aside className="community-aside">
              {kind === "REVIEW" ? (
                <>
                  <section className="panel">
                    <h3>Chia sẻ trải nghiệm</h3>
                    <FeedbackForm
                      key="review"
                      kind="REVIEW"
                      product={product}
                      user={user}
                      viewer={viewer}
                      onSent={refresh}
                      loading={remote.loading || !!remote.error}
                    />
                  </section>
                  <p className="community-rule fine">
                    <ShieldCheck size={17} /> Chỉ khách có đơn đã hoàn tất và
                    thanh toán mới được đánh giá.
                  </p>
                </>
              ) : (
                <>
                  <section className="panel">
                    <Headphones size={32} />
                    <h3>Cần hỗ trợ riêng?</h3>
                    <p className="subtle">
                      Tra cứu đơn hàng, đổi trả hoặc bảo hành.
                    </p>
                    <Link
                      className="button"
                      to={user ? "/orders" : "/login?next=%2Forders"}
                    >
                      Đơn hàng của tôi
                    </Link>
                  </section>
                  <section className="panel">
                    <h3>Hỏi đáp dễ dàng</h3>
                    <p>Đăng nhập để gửi câu hỏi</p>
                    <p>Có thể hỏi trước khi mua</p>
                    <p>Nhận phản hồi từ TechRetail</p>
                  </section>
                </>
              )}
            </aside>
          </div>
        )}
      </div>
    </section>
  );
}

function FeedbackForm({ kind, product, user, viewer, onSent, loading }) {
  const [rating, setRating] = useState(0),
    [title, setTitle] = useState(""),
    [body, setBody] = useState(""),
    [files, setFiles] = useState([]),
    [error, setError] = useState(""),
    [message, setMessage] = useState(""),
    [busy, setBusy] = useState(false);
  const lock = useRef(false),
    mounted = useRef(true);
  useEffect(() => {
    mounted.current = true;
    return () => {
      mounted.current = false;
    };
  }, []);
  const review = kind === "REVIEW";
  if (!user)
    return (
      <div className="community-signin">
        <p>
          {review
            ? "Đăng nhập tài khoản đã mua hàng để viết đánh giá."
            : "Đăng nhập để gửi câu hỏi và nhận phản hồi."}
        </p>
        <Link
          className="button"
          to={`/login?next=${encodeURIComponent("/products/" + product.slug)}`}
        >
          Đăng nhập
        </Link>
      </div>
    );
  if (review && viewer?.review_status)
    return (
      <p className="notice" role="status">
        Bạn đã gửi đánh giá cho sản phẩm này.{" "}
        {statusLabel[viewer.review_status] || "Đánh giá đã được duyệt."}
      </p>
    );
  if (review && viewer && !viewer.can_review)
    return (
      <p className="community-rule subtle">
        Bạn có thể viết đánh giá sau khi đơn hàng chứa sản phẩm này đã hoàn tất
        và thanh toán.
      </p>
    );
  if (review && !viewer)
    return (
      <p className="subtle">
        {loading
          ? "Đang kiểm tra điều kiện đánh giá…"
          : "Chưa thể kiểm tra điều kiện đánh giá. Vui lòng tải lại nội dung."}
      </p>
    );
  async function submit(e) {
    e.preventDefault();
    if (lock.current) return;
    if (review && !rating) {
      setError("Vui lòng chọn số sao.");
      return;
    }
    lock.current = true;
    setBusy(true);
    setError("");
    setMessage("");
    const data = new FormData();
    data.append("kind", kind);
    data.append("body", body);
    if (review) {
      data.append("rating", rating);
      data.append("title", title);
      files.forEach((file) => data.append("photos", file));
    }
    try {
      await api(`products/${product.slug}/feedback/`, {
        method: "POST",
        body: data,
      });
      if (!mounted.current) return;
      setBody("");
      setTitle("");
      setRating(0);
      setFiles([]);
      setMessage(
        review
          ? "Đã gửi đánh giá. Nội dung đang chờ duyệt."
          : "Đã gửi câu hỏi. Nội dung đang chờ duyệt.",
      );
      onSent();
    } catch (e) {
      if (mounted.current) setError(errorText(e));
    } finally {
      lock.current = false;
      if (mounted.current) setBusy(false);
    }
  }
  return (
    <form
      className={`community-form ${review ? "review-form" : "question-form"}`}
      onSubmit={submit}
    >
      {review && (
        <>
          <p className="community-purchased">
            <BadgeCheck size={18} /> Bạn đã mua sản phẩm này
          </p>
          <fieldset className="star-picker" disabled={busy || loading}>
            <legend>Số sao của bạn</legend>
            {[1, 2, 3, 4, 5].map((n) => (
              <button
                type="button"
                key={n}
                aria-label={`${n} sao`}
                aria-pressed={rating === n}
                onClick={() => setRating(n)}
              >
                <Star size={34} fill={n <= rating ? "currentColor" : "none"} />
              </button>
            ))}
          </fieldset>
          <Field label="Tiêu đề">
            <input
              maxLength={150}
              value={title}
              disabled={busy}
              placeholder="Trải nghiệm của bạn"
              onChange={(e) => setTitle(e.target.value)}
            />
          </Field>
        </>
      )}
      <Field label={review ? "Nội dung đánh giá" : "Câu hỏi của bạn"}>
        <textarea
          required
          minLength={5}
          maxLength={3000}
          value={body}
          disabled={busy}
          placeholder={
            review
              ? "Sản phẩm có đáp ứng mong đợi của bạn?"
              : "Hỏi về cấu hình, khả năng tương thích hoặc chính sách sản phẩm…"
          }
          onChange={(e) => setBody(e.target.value)}
        />
      </Field>
      {review && (
        <>
          <label className="community-upload">
            <Camera size={24} />
            <span>Thêm hình ảnh</span>
            <small>Tối đa 5 ảnh · JPG, PNG, WebP · 5 MB/ảnh</small>
            <input
              aria-label="Thêm hình ảnh đánh giá"
              type="file"
              accept="image/jpeg,image/png,image/webp"
              multiple
              disabled={busy}
              onChange={(e) => {
                const next = [...e.target.files];
                if (
                  next.length > 5 ||
                  next.some(
                    (f) =>
                      f.size > 5 * 1024 * 1024 ||
                      !["image/jpeg", "image/png", "image/webp"].includes(
                        f.type,
                      ),
                  )
                ) {
                  setError(
                    "Chọn tối đa 5 ảnh JPG, PNG hoặc WebP, mỗi ảnh tối đa 5 MB.",
                  );
                  e.target.value = "";
                  return;
                }
                setFiles(next);
                setError("");
              }}
            />
          </label>
          {files.length > 0 && (
            <ul className="community-files">
              {files.map((file, index) => (
                <li key={`${file.name}:${index}`}>
                  <span>{file.name}</span>
                  <button
                    type="button"
                    aria-label={`Bỏ ảnh ${file.name}`}
                    onClick={() =>
                      setFiles((previous) =>
                        previous.filter((_, i) => i !== index),
                      )
                    }
                  >
                    <X size={14} />
                  </button>
                </li>
              ))}
            </ul>
          )}
        </>
      )}
      <ErrorBox error={error} />
      {message && (
        <p className="notice" role="status">
          {message}
        </p>
      )}
      <button
        className="button primary"
        disabled={busy || loading || (review && !viewer?.can_review)}
      >
        {busy ? "Đang gửi…" : review ? "Gửi đánh giá" : "Gửi câu hỏi"}
        <Send size={16} />
      </button>
      <p className="fine">
        {review
          ? "Đánh giá sẽ được kiểm duyệt trước khi hiển thị."
          : "Không chia sẻ số điện thoại hoặc thông tin đơn hàng tại đây. Nội dung mới sẽ được kiểm duyệt."}
      </p>
    </form>
  );
}

function FeedbackThread({ item, user, onChange }) {
  const [reply, setReply] = useState(""),
    [showReply, setShowReply] = useState(false),
    [report, setReport] = useState(false),
    [reason, setReason] = useState(""),
    [busy, setBusy] = useState(false),
    [error, setError] = useState(""),
    [message, setMessage] = useState("");
  const lock = useRef(false),
    mounted = useRef(true);
  useEffect(() => {
    mounted.current = true;
    return () => {
      mounted.current = false;
    };
  }, []);
  async function send(path, body, method = "POST") {
    if (lock.current) return;
    lock.current = true;
    setBusy(true);
    setError("");
    setMessage("");
    try {
      await api(`feedback/${item.id}/${path}/`, { method, body });
      if (!mounted.current) return;
      setReply("");
      setReason("");
      setReport(false);
      setShowReply(false);
      if (path !== "helpful")
        setMessage(
          path === "report"
            ? "Đã gửi báo cáo."
            : "Đã gửi phản hồi để kiểm duyệt.",
        );
      onChange();
    } catch (e) {
      if (mounted.current) setError(errorText(e));
    } finally {
      lock.current = false;
      if (mounted.current) setBusy(false);
    }
  }
  return (
    <article className="community-thread">
      <header>
        <span className="community-avatar">
          {item.author.charAt(0).toUpperCase()}
        </span>
        <div>
          <strong>{item.author}</strong>
          <p className="fine">{dateTime(item.created_at)}</p>
        </div>
        {item.verified_purchase && (
          <span className="community-verified">
            <BadgeCheck size={15} /> Đã mua hàng
          </span>
        )}
        {item.status !== "APPROVED" && (
          <span className="community-pending">{statusLabel[item.status]}</span>
        )}
      </header>
      {item.kind === "REVIEW" && <Stars value={item.rating} />}
      {item.title && <h4>{item.title}</h4>}
      <p className="community-text">{item.body}</p>
      {item.photos.length > 0 && (
        <div className="community-photos">
          {item.photos.map((url, i) => (
            <a href={url} key={url} target="_blank" rel="noopener noreferrer">
              <img src={url} alt={`Ảnh đánh giá ${i + 1}`} loading="lazy" />
            </a>
          ))}
        </div>
      )}
      <div className="community-actions">
        <button
          type="button"
          disabled={busy || !user || item.status !== "APPROVED"}
          aria-pressed={item.helpful}
          onClick={() => send("helpful", { helpful: !item.helpful }, "PUT")}
        >
          <ThumbsUp size={15} /> Hữu ích ({item.helpful_count})
        </button>
        {item.kind === "QUESTION" && item.status === "APPROVED" && user && (
          <button
            type="button"
            disabled={busy}
            onClick={() => setShowReply(!showReply)}
          >
            <MessageCircle size={15} /> Trả lời
          </button>
        )}
        {user && !item.is_mine && item.status === "APPROVED" && (
          <button
            type="button"
            disabled={busy}
            onClick={() => setReport(!report)}
          >
            <Flag size={14} /> Báo cáo
          </button>
        )}
      </div>
      {item.replies.map((r) => (
        <div
          key={r.id}
          className={`community-reply ${r.is_staff_reply ? "staff" : ""}`}
        >
          <strong>{r.author}</strong>
          {r.is_staff_reply && (
            <span className="community-verified">
              <BadgeCheck size={14} /> Nhân viên
            </span>
          )}
          {r.status !== "APPROVED" && (
            <span className="community-pending">{statusLabel[r.status]}</span>
          )}
          <p className="community-text">{r.body}</p>
          <small className="fine">{dateTime(r.created_at)}</small>
        </div>
      ))}
      {item.kind === "QUESTION" &&
        !item.replies.some(
          (r) => r.is_staff_reply && r.status === "APPROVED",
        ) && <p className="fine">Đang chờ phản hồi từ TechRetail.</p>}
      {showReply && (
        <form
          className="community-inline-form"
          onSubmit={(e) => {
            e.preventDefault();
            send("replies", { body: reply });
          }}
        >
          <Field label="Phản hồi của bạn">
            <textarea
              value={reply}
              onChange={(e) => setReply(e.target.value)}
              minLength={2}
              maxLength={3000}
              required
              disabled={busy}
            />
          </Field>
          <button disabled={busy}>Gửi phản hồi</button>
        </form>
      )}
      {report && (
        <form
          className="community-inline-form"
          onSubmit={(e) => {
            e.preventDefault();
            send("report", { reason });
          }}
        >
          <Field label="Lý do báo cáo">
            <textarea
              required
              minLength={5}
              maxLength={500}
              value={reason}
              onChange={(e) => setReason(e.target.value)}
              disabled={busy}
            />
          </Field>
          <button disabled={busy}>Gửi báo cáo</button>
        </form>
      )}
      <ErrorBox error={error} />
      {message && (
        <p role="status" className="fine">
          {message}
        </p>
      )}
    </article>
  );
}
