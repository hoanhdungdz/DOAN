import React, { useState } from "react";
import { Ticket, CheckCircle2, Info, X } from "lucide-react";
import { ErrorBox } from "../../../shared/ui";

export default function CheckoutPromotions({
  quote,
  code,
  onSelect,
  loading,
  error,
  onRetry,
  disabled,
}) {
  const [input, setInput] = useState("");
  const apply = () => {
    const value = input.trim().toUpperCase();
    if (value) onSelect(value);
  };
  return (
    <section
      className="checkout-promotions"
      aria-label="Ưu đãi của cửa hàng"
      aria-busy={loading}
    >
      <h3>Ưu đãi của cửa hàng</h3>
      <div className="coupon-list">
        {(quote?.coupons || []).map((coupon) => {
          const selected =
            quote?.applied_coupon?.code === coupon.code && code === coupon.code;
          return (
            <article
              className={`coupon-ticket ${selected ? "selected" : ""} ${!coupon.eligible ? "unavailable" : ""}`}
              key={coupon.code}
            >
              <Ticket className="coupon-icon" size={25} aria-hidden="true" />
              <div className="coupon-copy">
                <strong>{coupon.code}</strong>
                <span>{coupon.benefit}</span>
                <small>
                  {coupon.first_order_only ? "Đơn đầu · " : ""}
                  {coupon.condition}
                </small>
                <small>
                  Mỗi khách {coupon.per_user_limit} lần · Hết hạn{" "}
                  {new Date(coupon.ends_at).toLocaleDateString("vi-VN")}
                </small>
                {!coupon.eligible && (
                  <small className="coupon-reason">{coupon.reason}</small>
                )}
              </div>
              <button
                type="button"
                aria-label={`${selected ? "Đã chọn" : "Dùng mã"} ${coupon.code}`}
                aria-pressed={selected}
                disabled={disabled || loading || !coupon.eligible || selected}
                onClick={() => {
                  setInput(coupon.code);
                  onSelect(coupon.code);
                }}
              >
                {selected ? (
                  <>
                    <CheckCircle2 size={15} /> Đã chọn
                  </>
                ) : coupon.eligible ? (
                  "Dùng mã"
                ) : (
                  "Chưa đủ điều kiện"
                )}
              </button>
            </article>
          );
        })}
      </div>
      <p className="coupon-hint">
        <Info size={14} aria-hidden="true" /> Mỗi đơn áp dụng 1 mã của cửa hàng.
      </p>
      <label className="coupon-input-label" htmlFor="checkout-coupon-code">
        Nhập mã giảm giá
      </label>
      <div className="coupon-entry">
        <input
          id="checkout-coupon-code"
          maxLength={32}
          placeholder="Nhập mã giảm giá"
          autoComplete="off"
          value={input}
          disabled={disabled}
          onChange={(e) => setInput(e.target.value.toUpperCase())}
          onKeyDown={(e) => {
            if (e.key === "Enter") {
              e.preventDefault();
              if (!loading && !disabled) apply();
            }
          }}
        />
        <button
          type="button"
          disabled={disabled || loading || !input.trim()}
          onClick={apply}
        >
          Áp dụng
        </button>
      </div>
      {loading && (
        <p className="coupon-hint" role="status">
          Đang kiểm tra ưu đãi…
        </p>
      )}
      <ErrorBox error={error || quote?.coupon_error} />
      {error && (
        <button type="button" onClick={onRetry} disabled={loading}>
          Thử lại ưu đãi
        </button>
      )}
      {code && !loading && (
        <div className="coupon-applied" role="status">
          <span>
            {quote?.applied_coupon ? (
              <>
                <CheckCircle2 size={16} /> Đã áp dụng {code}
              </>
            ) : (
              <>Mã đang kiểm tra: {code}</>
            )}
          </span>
          <button
            type="button"
            disabled={disabled}
            aria-label="Bỏ mã giảm giá"
            onClick={() => {
              setInput("");
              onSelect("");
            }}
          >
            <X size={14} /> Bỏ mã
          </button>
        </div>
      )}
    </section>
  );
}
