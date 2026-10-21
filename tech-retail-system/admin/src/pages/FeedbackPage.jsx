import React, { useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { BadgeCheck, MessageSquare, Star } from "lucide-react";
import { api, dateTime, errorText } from "../../../shared/api";
import { useSession } from "../../../shared/session";
import useRemote from "../../../shared/useRemote";
import { Empty, ErrorBox, Field, Loading, Pager } from "../../../shared/ui";
import "./FeedbackPage.css";

const labels = { PENDING: "Chờ duyệt", APPROVED: "Đã duyệt", HIDDEN: "Đã ẩn" };
export default function FeedbackPage() {
  const { user } = useSession();
  return user?.is_admin ? (
    <FeedbackManager key={user.id} />
  ) : (
    <ErrorBox error="Chỉ quản trị viên được duyệt nội dung và trả lời với tư cách TechRetail." />
  );
}
function FeedbackManager() {
  const [kind, setKind] = useState(""),
    [status, setStatus] = useState("PENDING"),
    [reported, setReported] = useState(false),
    [search, setSearch] = useState(""),
    [page, setPage] = useState(1),
    [revision, setRevision] = useState(0);
  const params = new URLSearchParams({ kind, status, reported, search, page }),
    remote = useRemote(`feedback-admin/?${params}`, revision);
  const filter = (setter) => (e) => {
    setter(e.target.value);
    setPage(1);
  };
  return (
    <>
      <div className="page-title">
        <div>
          <span className="eyebrow">NỘI DUNG KHÁCH HÀNG</span>
          <h1>Đánh giá & hỏi đáp</h1>
          <p className="subtle">
            Duyệt nội dung, kiểm tra báo cáo và phản hồi khách hàng.
          </p>
        </div>
        <MessageSquare size={32} />
      </div>
      <section className="panel">
        <div className="toolbar">
          <input
            aria-label="Tìm nội dung hoặc sản phẩm"
            placeholder="Tìm nội dung hoặc sản phẩm…"
            value={search}
            onChange={filter(setSearch)}
          />
          <select
            aria-label="Loại nội dung"
            value={kind}
            onChange={filter(setKind)}
          >
            <option value="">Tất cả nội dung</option>
            <option value="REVIEW">Đánh giá</option>
            <option value="QUESTION">Hỏi đáp</option>
          </select>
          <select
            aria-label="Trạng thái kiểm duyệt"
            value={status}
            onChange={filter(setStatus)}
          >
            <option value="">Mọi trạng thái</option>
            {Object.entries(labels).map(([value, label]) => (
              <option key={value} value={value}>
                {label}
              </option>
            ))}
          </select>
          <button
            aria-pressed={reported}
            onClick={() => {
              setReported(!reported);
              setPage(1);
            }}
          >
            {reported ? "Đang lọc báo cáo" : "Có báo cáo"}
          </button>
        </div>
        <ErrorBox error={remote.error} />
        {remote.error && (
          <button onClick={() => setRevision((n) => n + 1)}>Tải lại</button>
        )}
        {remote.loading ? (
          <Loading />
        ) : remote.data?.results.length ? (
          remote.data.results.map((item) => (
            <ModerationCard
              key={item.id}
              item={item}
              onChange={() => setRevision((n) => n + 1)}
            />
          ))
        ) : (
          !remote.error && <Empty text="Không có nội dung phù hợp." />
        )}
        {remote.data && (
          <Pager page={page} setPage={setPage} count={remote.data.count} />
        )}
      </section>
    </>
  );
}
function ModerationCard({ item, onChange }) {
  const [body, setBody] = useState(""),
    [busy, setBusy] = useState(false),
    [error, setError] = useState("");
  const lock = useRef(false),
    mounted = useRef(true);
  useEffect(() => {
    mounted.current = true;
    return () => {
      mounted.current = false;
    };
  }, []);
  async function action(path, method, payload) {
    if (lock.current) return;
    lock.current = true;
    setBusy(true);
    setError("");
    try {
      await api(path, { method, body: payload });
      if (mounted.current) {
        setBody("");
        onChange();
      }
    } catch (e) {
      if (mounted.current) setError(errorText(e));
    } finally {
      lock.current = false;
      if (mounted.current) setBusy(false);
    }
  }
  const controls = (id, state, reply = false) => (
    <div className="actions">
      {["APPROVED", "HIDDEN", "PENDING"]
        .filter((next) => next !== state)
        .map((next) => (
          <button
            key={next}
            disabled={busy}
            onClick={() =>
              action(
                `feedback-admin/${reply ? "replies/" : ""}${id}/`,
                "PATCH",
                { status: next },
              )
            }
          >
            {next === "APPROVED"
              ? "Duyệt hiển thị"
              : next === "HIDDEN"
                ? "Ẩn nội dung"
                : "Chuyển chờ duyệt"}
          </button>
        ))}
    </div>
  );
  return (
    <article className="feedback-moderation-card">
      <header>
        <span className="badge">
          {item.kind === "REVIEW" ? "Đánh giá" : "Hỏi đáp"}
        </span>
        <span className="badge">{labels[item.status]}</span>
        <span className="fine">{dateTime(item.created_at)}</span>
      </header>
      <h3>{item.product_name}</h3>
      <p className="subtle">
        {item.author}
        {item.verified_purchase && " · Đã mua hàng"}
      </p>
      {item.rating && (
        <p className="moderation-rating">
          <Star size={16} /> {item.rating}/5
        </p>
      )}
      {item.title && <strong>{item.title}</strong>}
      <p className="feedback-content">{item.body}</p>
      <div className="feedback-moderation-photos">
        {item.photos.map((url, index) => (
          <a key={url} href={url} target="_blank" rel="noopener noreferrer">
            <img src={url} alt={`Ảnh đính kèm ${index + 1}`} loading="lazy" />
          </a>
        ))}
      </div>
      {item.reports.length > 0 && (
        <div className="notice">
          <strong>{item.reports.length} báo cáo</strong>
          {item.reports.map((report, index) => (
            <p key={index} className="feedback-content">
              {report.reason}
            </p>
          ))}
        </div>
      )}
      {controls(item.id, item.status)}
      {item.replies.map((reply) => (
        <div className="feedback-moderation-reply" key={reply.id}>
          <strong>{reply.author}</strong>
          {reply.is_staff_reply && (
            <span>
              <BadgeCheck size={14} /> TechRetail
            </span>
          )}
          <span className="badge">{labels[reply.status]}</span>
          <p className="feedback-content">{reply.body}</p>
          {controls(reply.id, reply.status, true)}
        </div>
      ))}
      <form
        onSubmit={(e) => {
          e.preventDefault();
          action(`feedback/${item.id}/replies/`, "POST", { body });
        }}
      >
        <Field label="Phản hồi với tư cách TechRetail">
          <textarea
            minLength={2}
            maxLength={3000}
            required
            disabled={busy}
            value={body}
            onChange={(e) => setBody(e.target.value)}
          />
        </Field>
        <button className="button primary" disabled={busy}>
          {busy ? "Đang xử lý…" : "Gửi phản hồi"}
        </button>
      </form>
      <p className="fine">
        Phản hồi của TechRetail chỉ hiển thị công khai khi nội dung gốc đã được
        duyệt. Các phản hồi của khách đang chờ duyệt cũng nằm trong hàng chờ.
      </p>
      <Link to={`/products?search=${encodeURIComponent(item.product_name)}`}>
        Quản lý sản phẩm →
      </Link>
      <ErrorBox error={error} />
    </article>
  );
}
