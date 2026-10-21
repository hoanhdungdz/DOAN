import React from "react";
import { Link, useSearchParams } from "react-router-dom";
import {
  CheckCircle2,
  CircleAlert,
  LoaderCircle,
  ShieldCheck,
  XCircle,
} from "lucide-react";
import { useSession } from "../../../shared/session";
import { money } from "../../../shared/api";
import { ErrorBox, Loading } from "../../../shared/ui";
import useVnpayResult from "../../../shared/useVnpayResult";
import "./VnpayReturnPage.css";

export default function VnpayReturnPage() {
  const [params] = useSearchParams(),
    { user, loading, refresh } = useSession();
  const reference = params.get("reference"),
    valid = /^[a-f0-9]{32}$/.test(reference || "");
  return (
    <main className="content-width account-page vnpay-result-page">
      {loading ? (
        <Loading />
      ) : !user ? (
        <section className="panel vnpay-result-card">
          <h1>Xem kết quả thanh toán</h1>
          <p>Đăng nhập tài khoản đã đặt hàng để xem kết quả.</p>
          <Link className="button primary" to="/login?next=%2Forders">
            Đăng nhập
          </Link>
        </section>
      ) : !valid ? (
        <>
          <ErrorBox error="Thông tin trả về từ VNPay không hợp lệ. Vui lòng kiểm tra đơn hàng của bạn." />
          <Link to="/orders">Đơn hàng của tôi →</Link>
        </>
      ) : (
        <PaymentResult
          key={`${user.id}:${reference}`}
          reference={reference}
          refreshSession={refresh}
        />
      )}
    </main>
  );
}

const states = {
  verifying: [
    "Đang xác nhận thanh toán",
    "Vui lòng chờ trong giây lát. Kết quả sẽ tự động cập nhật tại đây.",
    LoaderCircle,
  ],
  success: [
    "Thanh toán thành công",
    "TechRetail đã nhận xác nhận thanh toán từ VNPay. Cảm ơn bạn đã mua sắm!",
    CheckCircle2,
  ],
  failed: [
    "Thanh toán chưa thành công",
    "VNPay xác nhận giao dịch chưa thành công hoặc đã bị hủy. Bạn có thể xem đơn hàng để tiếp tục.",
    XCircle,
  ],
  review: [
    "Giao dịch cần kiểm tra",
    "Vui lòng không thanh toán thêm. TechRetail cần đối soát giao dịch này với VNPay.",
    CircleAlert,
  ],
  refunded: [
    "Đã hoàn tiền",
    "Đơn hàng đã được ghi nhận hoàn tiền. Xem chi tiết trong đơn hàng của bạn.",
    CheckCircle2,
  ],
  unconfirmed: [
    "Chưa nhận được kết quả thanh toán",
    "Việc xác nhận đang mất nhiều thời gian hơn dự kiến. Nếu bạn đã thanh toán, vui lòng không thanh toán lại.",
    CircleAlert,
  ],
};

function PaymentResult({ reference, refreshSession }) {
  const { phase, attempt, order, error, retry } = useVnpayResult(
    reference,
    refreshSession,
  );
  if (phase === "denied")
    return (
      <section className="panel vnpay-result-card">
        <ErrorBox error={error} />
        <Link to="/login?next=%2Forders">Đăng nhập tài khoản đã đặt đơn</Link>
      </section>
    );
  const [title, description, Icon] = states[phase];
  const success = phase === "success",
    hasPromotion = Number(attempt?.promotion_amount) > 0;
  return (
    <section className={`panel vnpay-result-card ${phase}`}>
      <div
        className={`vnpay-result-icon ${phase === "verifying" ? "spin" : ""}`}
      >
        <Icon size={46} strokeWidth={1.7} aria-hidden="true" />
      </div>
      <span className="eyebrow">KẾT QUẢ THANH TOÁN VNPAY</span>
      <div role="status" aria-live="polite">
        <h1>{title}</h1>
        <p className="subtle">{description}</p>
      </div>
      {phase === "verifying" && (
        <p className="fine">
          Đơn hàng chỉ được ghi nhận đã thanh toán sau khi nhận xác nhận từ
          VNPay.
        </p>
      )}
      {phase === "review" && attempt?.review_reason && (
        <p className="notice">{attempt.review_reason}</p>
      )}
      {order && (
        <div className="vnpay-result-details">
          <div>
            <span>Đơn hàng</span>
            <strong>{order.code}</strong>
          </div>
          <div>
            <span>Phương thức</span>
            <strong>VNPay</strong>
          </div>
          {Number(order.discount_total) > 0 && (
            <div>
              <span>Mã cửa hàng {order.coupon_code}</span>
              <strong>−{money(order.discount_total)}</strong>
            </div>
          )}
          {hasPromotion && (
            <>
              <div>
                <span>Tổng đơn hàng sau mã cửa hàng</span>
                <strong>{money(order.grand_total)}</strong>
              </div>
              <div>
                <span>Ưu đãi VNPay {attempt.promotion_code}</span>
                <strong>−{money(attempt.promotion_amount)}</strong>
              </div>
            </>
          )}
          <div className="vnpay-result-total">
            <span>
              {success ? "Số tiền đã thanh toán" : "Số tiền giao dịch"}
            </span>
            <strong>
              {money(
                success && hasPromotion
                  ? attempt.customer_amount
                  : order.grand_total,
              )}
            </strong>
          </div>
          {attempt?.provider_transaction && (
            <div>
              <span>Mã giao dịch VNPay</span>
              <strong>{attempt.provider_transaction}</strong>
            </div>
          )}
        </div>
      )}
      {phase === "unconfirmed" && (
        <>
          <ErrorBox error={error} />
          <button className="button" onClick={retry}>
            Thử xác nhận lại
          </button>
        </>
      )}
      <div className="vnpay-result-actions">
        <Link
          className="button primary"
          to={order ? `/orders/${order.id}` : "/orders"}
        >
          Xem đơn hàng
        </Link>
        <Link className="button" to="/products">
          Tiếp tục mua sắm
        </Link>
      </div>
      <p className="fine vnpay-result-security">
        <ShieldCheck size={15} aria-hidden="true" />
        {success
          ? "Giao dịch đã được VNPay xác nhận."
          : "Kết quả được xác minh trực tiếp với VNPay."}
      </p>
      <details className="fine">
        <summary>Chi tiết giao dịch</summary>
        <p>Mã tham chiếu: {reference}</p>
      </details>
      <p className="fine vnpay-result-test">
        Môi trường thử nghiệm · Không sử dụng thông tin thanh toán thật.
      </p>
    </section>
  );
}
