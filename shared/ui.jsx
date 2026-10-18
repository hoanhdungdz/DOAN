import React, { useState } from "react";
import { imageSources } from "./productImages";
import { statusText } from "./status";
import {
  LoaderCircle,
  AlertCircle,
  PackageOpen,
  ArrowLeft,
  ArrowRight,
} from "lucide-react";
export function Loading() {
  return (
    <div className="state">
      <LoaderCircle className="spin" size={26} />
      <span>Đang tải dữ liệu…</span>
    </div>
  );
}
export function ErrorBox({ error }) {
  return error ? (
    <div className="error" role="alert">
      <AlertCircle size={18} />
      <span>{error}</span>
    </div>
  ) : null;
}
export function Empty({ text = "Chưa có dữ liệu để hiển thị." }) {
  return (
    <div className="state">
      <PackageOpen size={34} />
      <p>{text}</p>
    </div>
  );
}
export function ProductImage({ src, alt, ...props }) {
  return (
    <ResolvedProductImage
      key={src || "missing"}
      src={src}
      alt={alt}
      {...props}
    />
  );
}
function ResolvedProductImage({ src, alt, ...props }) {
  const sources = imageSources(src);
  const [attempt, setAttempt] = useState(0);
  const current = sources[attempt];
  const placeholder = current === "/placeholder.svg";
  return (
    <img
      {...props}
      src={current}
      decoding="async"
      referrerPolicy="no-referrer"
      alt={placeholder ? `Chưa có ảnh: ${alt || "sản phẩm"}` : alt}
      title={placeholder ? "Ảnh sản phẩm chưa khả dụng" : undefined}
      data-image-state={placeholder ? "unavailable" : "product"}
      onError={() =>
        setAttempt((index) => Math.min(index + 1, sources.length - 1))
      }
    />
  );
}
export function Pager({ page, setPage, count, size = 20 }) {
  return (
    <div className="pager">
      <span>
        {count} kết quả · Trang {page}/{Math.max(1, Math.ceil(count / size))}
      </span>
      <button
        aria-label="Trang trước"
        disabled={page === 1}
        onClick={() => setPage(page - 1)}
      >
        <ArrowLeft size={17} />
      </button>
      <button
        aria-label="Trang sau"
        disabled={page * size >= count}
        onClick={() => setPage(page + 1)}
      >
        <ArrowRight size={17} />
      </button>
    </div>
  );
}
export function Field({ label, children }) {
  const generatedId = React.useId();
  const control =
    React.isValidElement(children) &&
    ["input", "select", "textarea"].includes(children.type);
  const id = control ? children.props.id || generatedId : undefined;
  return (
    <div className="field">
      {control ? <label htmlFor={id}>{label}</label> : <span>{label}</span>}
      {control ? React.cloneElement(children, { id }) : children}
    </div>
  );
}
export function Badge({ children }) {
  return (
    <span
      className={`badge ${["COMPLETED", "PAID", "POSTED", "RECEIVED"].includes(children) ? "good" : ["CANCELLED", "REFUNDED"].includes(children) ? "muted" : ""}`}
    >
      {statusText(children)}
    </span>
  );
}
