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
    keys = useRef(new Map());
  const warehouses = useRemote("warehouses/?page_size=100");
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
    Promise.all(
      items.map(async (x) => {
        try {
          return { ...x, details: await api(`variants/${x.variant}/`) };
        } catch (error) {
          return { ...x, details: null, error: error.message };
        }
      }),
    )
      .then((d) => {
        if (live) {
          setDetails(d);
          setError("");
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
  ]);
  async function update(row, quantity) {
    try {
      await replace(
        items.map((x) => (x.variant === row.variant ? { ...x, quantity } : x)),
      );
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
    setBusy(true);
    setError("");
    const payload = {
      ...form,
      warehouse: Number(form.warehouse),
      items: items.map(({ variant, quantity }) => ({ variant, quantity })),
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
        <p>Giữ lại mã đơn để theo dõi tiến trình.</p>
        <code>{order.code}</code>
        <p>
          Tổng tiền: <b>{money(order.grand_total)}</b>
        </p>
        <p className="subtle">
          Đơn đang chờ xác nhận. Thanh toán: {order.payment_status}.
        </p>
        <Link to="/orders" className="button primary">
          Đơn hàng của tôi
        </Link>
        <Link to="/lookup" className="button">
          Tra cứu bằng OTP
        </Link>
      </main>
    );
  return (
    <main className="content-width cart-page">
      <span className="eyebrow">
        TECH RETAIL / {checkout ? "ĐẶT HÀNG" : "GIỎ HÀNG"}
      </span>
      <h1>{checkout ? "Chỉ còn một bước nữa." : "Lựa chọn của bạn."}</h1>
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
                    <strong>{money(row.details.price)}</strong>
                  ) : (
                    <p className="fine">
                      Vui lòng xóa sản phẩm này để tiếp tục.
                    </p>
                  )}
                </div>
                <input
                  aria-label={`Số lượng ${row.details?.product_name || "sản phẩm không còn bán"}`}
                  disabled={!row.details}
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
                      value={form.warehouse}
                      onChange={(e) =>
                        setForm({ ...form, warehouse: e.target.value })
                      }
                    >
                      <option value="">Chọn chi nhánh / kho</option>
                      {warehouses.data?.results?.map((w) => (
                        <option key={w.id} value={w.id}>
                          {w.store_name} — {w.name}
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
                      </select>
                    </Field>
                  </div>
                </div>
                <ErrorBox error={warehouses.error} />
                <p className="fine">
                  Chưa có cổng thanh toán tự động. Nếu chọn chuyển khoản, liên
                  hệ chi nhánh sau khi đơn được xác nhận.
                </p>
              </form>
            )}
          </section>
          <aside className="order-summary">
            <span className="eyebrow">TỔNG QUAN</span>
            <h2>Đơn hàng của bạn</h2>
            <div>
              <span>Tạm tính</span>
              <b>{money(fromMinorUnits(total))}</b>
            </div>
            <div>
              <span>Phí giao hàng</span>
              <b>0 ₫</b>
            </div>
            <div className="summary-total">
              <span>Tổng cộng</span>
              <strong>{money(fromMinorUnits(total))}</strong>
            </div>
            {checkout ? (
              <button
                form="checkout-form"
                className="button primary"
                disabled={
                  busy || !details.length || details.some((row) => !row.details)
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
          </aside>
        </div>
      )}
      <Link className="back-link" to="/products">
        ← Tiếp tục khám phá
      </Link>
    </main>
  );
}
