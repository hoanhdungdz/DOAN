import React, { useEffect, useRef, useState } from "react";
import { toMinorUnits, fromMinorUnits } from "../../../shared/money";
import { Link, useLocation } from "react-router-dom";
import { Trash2, ArrowRight, CheckCircle2 } from "lucide-react";
import { useCart } from "../features/cart/CartContext";
import { api, money, errorText, operationKey } from "../../../shared/api";
import {
  Loading,
  ErrorBox,
  Empty,
  Field,
  ProductImage,
} from "../../../shared/ui";
import useRemote from "../hooks/useRemote";
import CheckoutPromotions from "../components/CheckoutPromotions";
import { statusText } from "../../../shared/status";
import {
  checkoutWarehouses,
  warehouseStockLabel,
} from "../../../shared/checkoutStock";
export default function CartCheckout({ checkout = false }) {
  const location = useLocation();
  const {
      items,
      replace,
      clear,
      loading: cartLoading,
      error: cartError,
    } = useCart(),
    [details, setDetails] = useState([]),
    [loading, setLoading] = useState(true),
    [error, setError] = useState(""),
    [busy, setBusy] = useState(false),
    [order, setOrder] = useState(null),
    [stockRevision, setStockRevision] = useState(0),
    keys = useRef(new Map());
  const warehouses = useRemote("warehouses/?page_size=100");
  const features = useRemote("features/");
  const [couponCode, setCouponCode] = useState("");
  const [quoteState, setQuoteState] = useState({
    key: "",
    data: null,
    error: "",
  });
  const basket = items.map(({ variant, quantity }) => ({ variant, quantity }));
  const quoteKey = JSON.stringify({ items: basket, coupon_code: couponCode });
  const quote = quoteState.key === quoteKey ? quoteState.data : null;
  const quoteError = quoteState.key === quoteKey ? quoteState.error : "";
  const quoteReady = Boolean(quote && !quoteError);
  useEffect(() => {
    if (!checkout || !basket.length || order) return;
    let live = true;
    setQuoteState({ key: quoteKey, data: null, error: "" });
    api("checkout/promotions/", { method: "POST", body: JSON.parse(quoteKey) })
      .then((data) => {
        if (live) setQuoteState({ key: quoteKey, data, error: "" });
      })
      .catch((e) => {
        if (live)
          setQuoteState({ key: quoteKey, data: null, error: errorText(e) });
      });
    return () => {
      live = false;
    };
  }, [quoteKey, checkout, stockRevision, order?.id]);
  const [form, setForm] = useState({
    warehouse: "",
    recipient_name: "",
    phone: "",
    address: "",
    fulfillment: "DELIVERY",
    payment_method: "COD",
  });
  useEffect(() => {
    let live = true;
    setLoading(true);
    const load =
      checkout && items.length
        ? api("carts/availability/", {
            method: "POST",
            body: {
              items: items.map(({ variant, quantity }) => ({
                variant,
                quantity,
              })),
            },
          }).then((result) => result.items)
        : Promise.all(
            items.map(async (x) => {
              try {
                return { ...x, details: await api(`variants/${x.variant}/`) };
              } catch (error) {
                return { ...x, details: null, error: error.message };
              }
            }),
          );
    load
      .then((d) => {
        if (live) {
          setDetails(d);
        }
      })
      .catch((e) => {
        if (live) setError(errorText(e));
      })
      .finally(() => {
        if (live) setLoading(false);
      });
    return () => {
      live = false;
    };
  }, [
    JSON.stringify(
      items.map(({ variant, quantity }) => ({ variant, quantity })),
    ),
    stockRevision,
    checkout,
  ]);
  const warehouseChoices = checkoutWarehouses(
    warehouses.data?.results || [],
    details,
  );
  const selectedWarehouse = warehouseChoices.find(
    (w) => String(w.id) === String(form.warehouse),
  );
  const suggestedWarehouse = warehouseChoices.find((w) => w.sufficient);
  useEffect(() => {
    if (
      checkout &&
      !loading &&
      !cartLoading &&
      !form.warehouse &&
      suggestedWarehouse
    )
      setForm((previous) =>
        previous.warehouse
          ? previous
          : { ...previous, warehouse: String(suggestedWarehouse.id) },
      );
  }, [checkout, loading, cartLoading, form.warehouse, suggestedWarehouse?.id]);
  useEffect(() => {
    if (!checkout) return;
    const refreshStock = () => setStockRevision((value) => value + 1);
    window.addEventListener("focus", refreshStock);
    return () => window.removeEventListener("focus", refreshStock);
  }, [checkout]);
  async function update(row, quantity) {
    try {
      await replace(
        items.map((x) => (x.variant === row.variant ? { ...x, quantity } : x)),
      );
      setError("");
    } catch (e) {
      setError(errorText(e));
    }
  }
  const total = details.reduce(
    (n, x) =>
      n + (x.details ? toMinorUnits(x.details.price) * BigInt(x.quantity) : 0n),
    0n,
  );
  async function submit(e) {
    e.preventDefault();
    if (checkout && (!quoteReady || quote.coupon_error)) {
      setError(
        "Vui lòng kiểm tra ưu đãi hoặc bỏ mã chưa hợp lệ trước khi đặt hàng.",
      );
      return;
    }
    if (loading || !selectedWarehouse?.sufficient) {
      setError("Vui lòng chọn chi nhánh có đủ tất cả sản phẩm trong giỏ hàng.");
      return;
    }
    setBusy(true);
    setError("");
    const payload = {
      ...form,
      warehouse: Number(form.warehouse),
      items: items.map(({ variant, quantity }) => ({ variant, quantity })),
      coupon_code: couponCode,
      quoted_total: quote.grand_total,
    };
    try {
      const result = await api("orders/", {
        method: "POST",
        body: payload,
        headers: {
          "Idempotency-Key": operationKey(keys.current, "checkout", payload),
        },
      });
      setOrder(result);
      try {
        await clear();
      } catch {
        /* Order succeeded; retrying checkout must not be suggested on cart cleanup failure. */
      }
    } catch (e) {
      setError(errorText(e));
      if (
        ["INSUFFICIENT_STOCK", "COUPON_INVALID", "PRICE_CHANGED"].includes(
          e.code,
        )
      )
        setStockRevision((value) => value + 1);
    } finally {
      setBusy(false);
    }
  }
  if (order)
    return (
      <main className="success panel">
        <CheckCircle2 size={42} />
        <span className="eyebrow">ĐẶT HÀNG THÀNH CÔNG</span>
        <h1>Cảm ơn bạn đã lựa chọn.</h1>
        <p>Đơn đã được lưu vào tài khoản của bạn.</p>
        <code>{order.code}</code>
        <p>
          Tổng tiền: <b>{money(order.grand_total)}</b>
        </p>
        <p className="subtle">
          Đơn đang chờ xác nhận. {statusText(order.payment_status)}.
        </p>
        <Link to={"/orders/" + order.id} className="button primary">
          {order.payment_method === "VNPAY_SANDBOX"
            ? "Thanh toán qua VNPay"
            : "Xem chi tiết đơn hàng"}
        </Link>
        <Link to="/orders" className="button">
          Đơn hàng của tôi
        </Link>
      </main>
    );
  return (
    <main className="content-width cart-page">
      <span className="eyebrow">
        TECH RETAIL / {checkout ? "ĐẶT HÀNG" : "GIỎ HÀNG"}
      </span>
      <h1>{checkout ? "Thanh toán" : "Lựa chọn của bạn."}</h1>
      {checkout && <p className="subtle">Hoàn tất thông tin để đặt hàng.</p>}
      <ErrorBox error={error || cartError || location.state?.notice} />
      {loading || cartLoading ? (
        <Loading />
      ) : !items.length ? (
        <Empty text="Giỏ hàng đang trống. Khám phá thiết bị và thêm lựa chọn của bạn." />
      ) : (
        <div className="checkout-grid">
          <section>
            {details.map((row) => (
              <article className="cart-row" key={row.variant}>
                <Link
                  to={
                    row.details
                      ? "/products/" + row.details.product_slug
                      : "/products"
                  }
                >
                  <ProductImage
                    src={row.details?.image}
                    alt={row.details?.product_name || "Sản phẩm không còn bán"}
                  />
                </Link>
                <div>
                  <small>{row.details?.sku || "Không còn bán"}</small>
                  <h3>
                    {row.details?.product_name || "Sản phẩm đã ngừng bán"}
                  </h3>
                  {row.details ? (
                    <>
                      <strong>{money(row.details.price)}</strong>
                      {checkout && selectedWarehouse && (
                        <p className="fine cart-stock">
                          Còn{" "}
                          {selectedWarehouse.lines.find(
                            (line) => line.variant === row.variant,
                          )?.available ?? 0}{" "}
                          tại {selectedWarehouse.store_name} · Bạn cần{" "}
                          {row.quantity}
                        </p>
                      )}
                    </>
                  ) : (
                    <p className="fine">
                      Vui lòng xóa sản phẩm này để tiếp tục.
                    </p>
                  )}
                </div>
                <input
                  aria-label={`Số lượng ${row.details?.product_name || "sản phẩm không còn bán"}`}
                  disabled={busy || !row.details}
                  type="number"
                  min="1"
                  max="1000"
                  value={row.quantity}
                  onChange={(e) => {
                    const n = Number(e.target.value);
                    if (Number.isInteger(n) && n > 0) update(row, n);
                  }}
                />
                <button
                  aria-label="Xóa khỏi giỏ"
                  disabled={busy}
                  onClick={() => update(row, 0)}
                >
                  <Trash2 size={17} />
                </button>
              </article>
            ))}
            {checkout && (
              <form
                id="checkout-form"
                className="panel checkout-form"
                onSubmit={submit}
              >
                <h3>Thông tin nhận hàng</h3>
                <div className="form-grid">
                  <Field label="Họ và tên người nhận">
                    <input
                      required
                      maxLength={150}
                      value={form.recipient_name}
                      onChange={(e) =>
                        setForm({ ...form, recipient_name: e.target.value })
                      }
                    />
                  </Field>
                  <Field label="Số điện thoại">
                    <input
                      required
                      type="tel"
                      value={form.phone}
                      onChange={(e) =>
                        setForm({ ...form, phone: e.target.value })
                      }
                    />
                  </Field>
                  <Field label="Hình thức nhận">
                    <select
                      value={form.fulfillment}
                      onChange={(e) =>
                        setForm({ ...form, fulfillment: e.target.value })
                      }
                    >
                      <option value="DELIVERY">Giao hàng</option>
                      <option value="PICKUP">Nhận tại cửa hàng</option>
                    </select>
                  </Field>
                  <Field label="Chi nhánh xử lý đơn">
                    <select
                      required
                      disabled={busy || warehouses.loading}
                      value={form.warehouse}
                      onChange={(e) => {
                        setForm({ ...form, warehouse: e.target.value });
                        setError("");
                      }}
                    >
                      <option value="">Chọn chi nhánh / kho</option>
                      {warehouseChoices.map((w) => (
                        <option
                          key={w.id}
                          value={w.id}
                          disabled={!w.sufficient}
                        >
                          {warehouseStockLabel(w)}
                        </option>
                      ))}
                    </select>
                  </Field>
                  <div className="wide">
                    <Field label="Địa chỉ nhận hàng">
                      <input
                        required={form.fulfillment === "DELIVERY"}
                        maxLength={500}
                        value={form.address}
                        onChange={(e) =>
                          setForm({ ...form, address: e.target.value })
                        }
                      />
                    </Field>
                  </div>
                  <div className="wide">
                    <Field label="Phương thức thanh toán">
                      <select
                        value={form.payment_method}
                        onChange={(e) =>
                          setForm({ ...form, payment_method: e.target.value })
                        }
                      >
                        <option value="COD">
                          COD — thu tiền khi giao / nhận
                        </option>
                        <option value="BANK_TRANSFER">
                          Chuyển khoản — nhân viên xác nhận
                        </option>
                        <option
                          value="VNPAY_SANDBOX"
                          disabled={!features.data?.vnpay_sandbox}
                        >
                          VNPay (QR / thẻ ngân hàng)
                          {!features.data?.vnpay_sandbox
                            ? " — chưa khả dụng"
                            : ""}
                        </option>
                      </select>
                    </Field>
                  </div>
                </div>
                <ErrorBox error={warehouses.error} />
                {!warehouses.loading &&
                  !warehouses.error &&
                  !selectedWarehouse?.sufficient && (
                    <ErrorBox
                      error={
                        suggestedWarehouse
                          ? "Chi nhánh đang chọn không đủ hàng. Vui lòng chọn chi nhánh khác."
                          : "Chưa có chi nhánh đủ tất cả sản phẩm trong giỏ. Hãy giảm số lượng hoặc tách giỏ hàng."
                      }
                    />
                  )}
              </form>
            )}
          </section>
          <aside
            className={`order-summary ${checkout ? "checkout-summary" : ""}`}
          >
            <span className="eyebrow">TỔNG QUAN</span>
            <h2>Đơn hàng của bạn</h2>
            {checkout && (
              <CheckoutPromotions
                quote={quote}
                code={couponCode}
                loading={!quoteReady && !quoteError}
                error={quoteError}
                disabled={busy}
                onRetry={() => setStockRevision((n) => n + 1)}
                onSelect={(code) => {
                  setCouponCode(code);
                  setError("");
                }}
              />
            )}
            <div>
              <span>Tạm tính</span>
              <b>{money(quote?.subtotal ?? fromMinorUnits(total))}</b>
            </div>
            {checkout && quote?.applied_coupon && (
              <div className="summary-discount">
                <span>Giảm giá {quote.applied_coupon.code}</span>
                <b>−{money(quote.discount_total)}</b>
              </div>
            )}
            <div>
              <span>Phí giao hàng</span>
              <b>0 ₫</b>
            </div>
            <div className="summary-total">
              <span>Tổng cộng</span>
              <strong>
                {money(quote?.grand_total ?? fromMinorUnits(total))}
              </strong>
            </div>
            {checkout ? (
              <button
                form="checkout-form"
                className="button primary"
                disabled={
                  busy ||
                  !quoteReady ||
                  Boolean(quote?.coupon_error) ||
                  warehouses.loading ||
                  !selectedWarehouse?.sufficient ||
                  !details.length ||
                  details.some((row) => !row.details)
                }
              >
                {busy ? "Đang đặt hàng…" : "Xác nhận đặt hàng"}
                <ArrowRight size={17} />
              </button>
            ) : (
              <Link to="/checkout" className="button primary">
                Tiến hành đặt hàng <ArrowRight size={17} />
              </Link>
            )}
            <p className="fine">
              Giá chính thức được máy chủ xác nhận. Giỏ hàng chưa giữ tồn kho.
            </p>
            {checkout && form.payment_method === "VNPAY_SANDBOX" && (
              <p className="fine">
                Ưu đãi riêng của VNPay được kiểm tra tại cổng thanh toán.
              </p>
            )}
          </aside>
        </div>
      )}
      <Link className="back-link" to="/products">
        ← Tiếp tục khám phá
      </Link>
    </main>
  );
}
