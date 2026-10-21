import React, { useEffect, useRef, useState } from "react";
import { api, dateTime, errorText, money } from "./api";
import { ErrorBox } from "./ui";
import { useSession } from "./session";
import {
  ArrowRight,
  CheckCircle2,
  CreditCard,
  ShieldCheck,
} from "lucide-react";
import { redirectToVnpay, safeVnpayUrl } from "./vnpayNavigation";
export { safeVnpayUrl } from "./vnpayNavigation";

export default function VnpayPaymentPanel({ order, onChange }) {
  const { user, refresh } = useSession();
  return (
    <PaymentPanel
      key={`${user?.id}:${order.id}`}
      order={order}
      onChange={onChange}
      refreshSession={refresh}
    />
  );
}

function PaymentPanel({ order, onChange, refreshSession }) {
  const [payment, setPayment] = useState(order.vnpay_payment),
    [enabled, setEnabled] = useState(false),
    [busy, setBusy] = useState(""),
    [error, setError] = useState(""),
    [revision, setRevision] = useState(0),
    [waiting, setWaiting] = useState(false),
    [denied, setDenied] = useState(false);
  const busyRef = useRef(false),
    mounted = useRef(true),
    latest = useRef({ order, onChange, refreshSession });
  latest.current = { order, onChange, refreshSession };
  useEffect(() => {
    mounted.current = true;
    return () => {
      mounted.current = false;
    };
  }, []);
  const handleError = (e) => {
    if (!mounted.current) return;
    if ([401, 403, 404].includes(e.status)) {
      setPayment(null);
      setWaiting(false);
      setDenied(true);
      setError(
        "Không tìm thấy thanh toán của tài khoản này. Hãy đăng nhập tài khoản đã đặt đơn.",
      );
      latest.current.refreshSession?.();
    } else setError(errorText(e));
  };
  const accept = (data) => {
    setPayment(data);
    setError("");
    if (
      data.order_payment_status &&
      data.order_payment_status !== latest.current.order.payment_status
    )
      latest.current.onChange?.();
  };
  const reference = payment?.reference;
  useEffect(() => {
    let live = true;
    api("features/")
      .then((f) => {
        if (live) setEnabled(f.vnpay_sandbox === true);
      })
      .catch(() => {});
    return () => {
      live = false;
    };
  }, []);
  useEffect(() => {
    if (!reference) return;
    let live = true,
      fetching = false,
      timer;
    const deadline = Date.now() + 60000;
    const refresh = async () => {
      if (fetching) return;
      fetching = true;
      try {
        const data = await api(`payments/vnpay/attempts/${reference}/`);
        if (!live) return;
        accept(data);
        const pending =
          data.status === "PENDING" &&
          new Date(data.expires_at).getTime() > Date.now();
        setWaiting(pending && Date.now() < deadline);
        if (!pending || Date.now() >= deadline) clearInterval(timer);
      } catch (e) {
        if (live) {
          handleError(e);
          if ([401, 403, 404].includes(e.status)) clearInterval(timer);
        }
      } finally {
        fetching = false;
      }
    };
    refresh();
    timer = setInterval(() => {
      if (Date.now() >= deadline) {
        clearInterval(timer);
        if (live) setWaiting(false);
      } else if (document.visibilityState !== "hidden") refresh();
    }, 4000);
    return () => {
      live = false;
      clearInterval(timer);
    };
  }, [reference, revision]);
  const paid =
    order.payment_status === "PAID" || payment?.order_payment_status === "PAID";
  const review =
    payment?.status === "REVIEW" || order.payment_status === "REFUND_PENDING";
  const active =
    payment?.status === "PENDING" &&
    new Date(payment.expires_at).getTime() > Date.now();
  const canPay =
    !paid &&
    !review &&
    ["PENDING", "CONFIRMED", "PACKING"].includes(order.status);
  const hasPromotion = Number(payment?.promotion_amount) > 0;
  async function pay() {
    if (busyRef.current) return;
    busyRef.current = true;
    setBusy("pay");
    setError("");
    try {
      // Revalidate ownership and order state, and reuse an active request on the server.
      const data = await api(`my-orders/${order.id}/vnpay/`, {
        method: "POST",
        body: { bank_mode: "" },
      });
      if (!mounted.current) return;
      if (!safeVnpayUrl(data.payment_url))
        throw new Error("Địa chỉ thanh toán VNPay không hợp lệ.");
      setPayment(data);
      setRevision((r) => r + 1);
      redirectToVnpay(data.payment_url);
    } catch (e) {
      handleError(e);
    } finally {
      busyRef.current = false;
      if (mounted.current) setBusy("");
    }
  }
  if (denied)
    return (
      <section className="panel vnpay-panel">
        <ErrorBox error={error} />
        <a href="/login?next=%2Forders">Đăng nhập tài khoản đã đặt đơn</a>
      </section>
    );
  return (
    <section className="panel vnpay-panel">
      <div className="vnpay-heading">
        <div className="vnpay-title">
          <span className="vnpay-icon">
            <CreditCard size={24} aria-hidden="true" />
          </span>
          <div>
            <span className="eyebrow">THANH TOÁN TRỰC TUYẾN</span>
            <h3>Thanh toán qua VNPay</h3>
          </div>
        </div>
        <span
          className={`vnpay-status ${review ? "review" : paid ? "paid" : "pending"}`}
        >
          {review ? "Cần kiểm tra" : paid ? "Đã thanh toán" : "Chưa thanh toán"}
        </span>
      </div>
      <div className="vnpay-body">
        <div className="vnpay-information">
          <p className="subtle">
            Đơn hàng <strong>{order.code}</strong>
          </p>
          <p>
            Thanh toán bằng mã QR, thẻ ngân hàng hoặc ví điện tử trên VNPay.
          </p>
          {Number(order.discount_total) > 0 && (
            <p className="vnpay-offer">
              Mã cửa hàng {order.coupon_code}: −{money(order.discount_total)}
              <span className="fine">Đã trừ vào tổng đơn hàng.</span>
            </p>
          )}
          {hasPromotion ? (
            <div className="vnpay-offer" aria-label="Ưu đãi VNPay">
              <p>
                Ưu đãi VNPay {payment.promotion_code}: −
                {money(payment.promotion_amount)}
              </p>
              <span className="fine">
                Ưu đãi đã được VNPay xác nhận, áp dụng thêm sau mã cửa hàng.
              </span>
            </div>
          ) : (
            !paid &&
            !review && (
              <p className="fine">
                Bạn có thể dùng thêm ưu đãi VNPay tại bước thanh toán nếu đáp
                ứng điều kiện của chương trình.
              </p>
            )
          )}
          <p className="vnpay-security">
            <ShieldCheck size={17} aria-hidden="true" /> Giao dịch được xác thực
            qua VNPay
          </p>
        </div>
        <div className="vnpay-summary">
          <span className="subtle">
            {paid ? "Số tiền đã thanh toán" : "Số tiền cần thanh toán"}
          </span>
          <strong className="vnpay-amount">
            {money(
              paid && hasPromotion
                ? payment.customer_amount
                : order.grand_total,
            )}
          </strong>
          {hasPromotion && (
            <p className="fine">Tổng đơn hàng: {money(order.grand_total)}</p>
          )}
          <ErrorBox error={error} />
          {review ? (
            <div className="notice" role="status">
              {payment?.review_reason ||
                "Giao dịch cần được kiểm tra hoàn tiền với VNPay."}
            </div>
          ) : paid ? (
            <p className="vnpay-confirmed" role="status">
              <CheckCircle2 size={19} aria-hidden="true" /> Đã nhận xác nhận
              thanh toán từ VNPay.
            </p>
          ) : (
            <>
              {payment?.status === "FAILED" && (
                <p role="status">
                  Thanh toán chưa thành công hoặc đã bị hủy. Vui lòng thử lại.
                </p>
              )}
              {payment && !active && payment.status === "PENDING" && (
                <p role="status">
                  Lần thanh toán trước đã hết hạn. Bạn có thể thanh toán lại nếu
                  đơn hàng còn hiệu lực.
                </p>
              )}
              {canPay ? (
                <>
                  <button
                    className="button primary vnpay-pay"
                    disabled={Boolean(busy) || !enabled}
                    onClick={pay}
                  >
                    {busy === "pay"
                      ? "Đang chuyển đến VNPay…"
                      : "Thanh toán ngay"}
                    <ArrowRight size={18} aria-hidden="true" />
                  </button>
                  <p className="fine">
                    {enabled
                      ? "Bạn sẽ được chuyển đến VNPay để chọn phương thức thanh toán."
                      : "VNPay hiện chưa khả dụng. Vui lòng thử lại sau."}
                  </p>
                  {active && (
                    <p className="fine">
                      Hoàn tất trước {dateTime(payment.expires_at)}.
                    </p>
                  )}
                </>
              ) : (
                <p>Đơn hàng không còn ở trạng thái có thể thanh toán.</p>
              )}
            </>
          )}
          {reference && !paid && !review && (
            <button
              className="button vnpay-check"
              disabled={Boolean(busy)}
              onClick={async () => {
                if (busyRef.current) return;
                busyRef.current = true;
                setBusy("check");
                setError("");
                try {
                  const data = await api(
                    `payments/vnpay/attempts/${reference}/check/`,
                    { method: "POST", body: {} },
                  );
                  if (mounted.current) {
                    accept(data);
                    setRevision((r) => r + 1);
                  }
                } catch (e) {
                  handleError(e);
                } finally {
                  busyRef.current = false;
                  if (mounted.current) setBusy("");
                }
              }}
            >
              {busy === "check"
                ? "Đang kiểm tra…"
                : "Kiểm tra kết quả thanh toán"}
            </button>
          )}
          {reference && !paid && !review && (
            <p className="fine" role="status">
              {waiting
                ? "Đang chờ xác nhận từ VNPay…"
                : "Nếu vừa thanh toán, hãy kiểm tra lại kết quả. Đơn chỉ cập nhật sau khi nhận xác nhận từ VNPay."}
            </p>
          )}
        </div>
      </div>
      <div className="vnpay-footer">
        <p className="fine">
          Môi trường thử nghiệm · Sử dụng tài khoản hoặc thẻ test do VNPay cung
          cấp.
        </p>
        {reference && (
          <details className="fine">
            <summary>Chi tiết giao dịch</summary>
            <p>
              Mã yêu cầu: {reference}
              {payment?.provider_transaction
                ? ` · Giao dịch: ${payment.provider_transaction}`
                : ""}
            </p>
          </details>
        )}
      </div>
    </section>
  );
}
