import React, { useRef, useState } from "react";
import { toMinorUnits, fromMinorUnits } from "../../../shared/money";
import { Link } from "react-router-dom";
import { Search, Plus, Trash2, ShoppingBag } from "lucide-react";
import { api, money, errorText, operationKey } from "../../../shared/api";
import {
  Loading,
  ErrorBox,
  Field,
  ProductImage,
  Empty,
  Pager,
} from "../../../shared/ui";
import { useSession } from "../../../shared/session";
import useRemote from "../hooks/useRemote";
export default function POSPage() {
  const { user } = useSession(),
    [search, setSearch] = useState(""),
    [customerSearch, setCustomerSearch] = useState(""),
    [page, setPage] = useState(1),
    [items, setItems] = useState([]),
    [error, setError] = useState(""),
    [busy, setBusy] = useState(false),
    [order, setOrder] = useState(null),
    keys = useRef(new Map());
  const [form, setForm] = useState({
      warehouse: "",
      customer: "",
      recipient_name: "",
      phone: "",
      payment_method: "CASH",
    }),
    products = useRemote(
      "variants/?" +
        new URLSearchParams({
          search,
          page,
          store: form.warehouse ? "" : "",
          page_size: 12,
        }),
    ),
    warehouses = useRemote("warehouses/?page_size=100&scope=sales");
  const selectedStore = warehouses.data?.results?.find(
    (w) => String(w.id) === form.warehouse,
  )?.store;
  const customers = useRemote(
    "customers/?" +
      new URLSearchParams({
        page_size: 100,
        search: customerSearch,
        ...(!user.is_admin && selectedStore ? { store: selectedStore } : {}),
      }),
  );
  const sum = items.reduce(
    (n, i) => n + toMinorUnits(i.details.price) * BigInt(i.quantity),
    0n,
  );
  async function draft(e) {
    e.preventDefault();
    setBusy(true);
    setError("");
    const payload = {
      ...form,
      warehouse: Number(form.warehouse),
      customer: form.customer ? Number(form.customer) : undefined,
      channel: "IN_STORE",
      fulfillment: "PICKUP",
      address: "",
      items: items.map(({ variant, quantity }) => ({ variant, quantity })),
    };
    try {
      const o = await api("orders/", {
        method: "POST",
        body: payload,
        headers: {
          "Idempotency-Key": operationKey(keys.current, "pos", payload),
        },
      });
      setOrder(o);
    } catch (e) {
      setError(errorText(e));
    } finally {
      setBusy(false);
    }
  }
  return (
    <>
      <div className="page-title">
        <div>
          <span className="eyebrow">BÁN HÀNG / TẠI QUẦY</span>
          <h1>Tạo đơn tại quầy</h1>
          <p className="subtle">
            Đơn nháp chưa giữ hàng. Kiểm tra tồn và thu tiền khi chốt bán.
          </p>
        </div>
        <ShoppingBag size={28} />
      </div>
      <ErrorBox error={error} />
      {order ? (
        <section className="panel success">
          <h2>Đã tạo đơn nháp {order.code}</h2>
          <p>Tổng tiền từ máy chủ: {money(order.grand_total)}</p>
          <p className="subtle">
            Mở chi tiết đơn, kiểm tra thanh toán rồi chọn “Chốt bán & thu tiền”.
          </p>
          <Link to={"/orders/" + order.id} className="button primary">
            Mở đơn để chốt bán →
          </Link>
        </section>
      ) : (
        <div className="pos-grid">
          <section className="panel">
            <div className="search-input">
              <Search size={16} />
              <input
                placeholder="Tên sản phẩm hoặc SKU…"
                value={search}
                onChange={(e) => {
                  setSearch(e.target.value);
                  setPage(1);
                }}
              />
            </div>
            <ErrorBox error={products.error} />
            {products.loading ? (
              <Loading />
            ) : products.data?.results?.length ? (
              <div className="pos-products">
                {products.data.results.map((v) => (
                  <button
                    key={v.id}
                    onClick={() => {
                      const found = items.find((i) => i.variant === v.id);
                      setItems(
                        found
                          ? items.map((i) =>
                              i.variant === v.id
                                ? { ...i, quantity: i.quantity + 1 }
                                : i,
                            )
                          : [
                              ...items,
                              { variant: v.id, quantity: 1, details: v },
                            ],
                      );
                    }}
                  >
                    <ProductImage src={v.image} alt={v.product_name} />
                    <small>{v.sku}</small>
                    <strong>{v.product_name}</strong>
                    <span>
                      {money(v.price)} <Plus size={14} />
                    </span>
                  </button>
                ))}
              </div>
            ) : (
              <Empty />
            )}
            {products.data && (
              <Pager
                page={page}
                setPage={setPage}
                count={products.data.count}
                size={12}
              />
            )}
          </section>
          <aside className="panel">
            <h3>Thông tin đơn bán</h3>
            <form onSubmit={draft}>
              <Field label="Kho xuất">
                <select
                  required
                  value={form.warehouse}
                  onChange={(e) =>
                    setForm({
                      ...form,
                      warehouse: e.target.value,
                      customer: "",
                      ...(form.customer
                        ? { recipient_name: "", phone: "" }
                        : {}),
                    })
                  }
                >
                  <option value="">Chọn kho</option>
                  {warehouses.data?.results
                    ?.filter((w) => user.stores.includes(w.store))
                    .map((w) => (
                      <option key={w.id} value={w.id}>
                        {w.store_name} — {w.name}
                      </option>
                    ))}
                </select>
              </Field>
              <Field label="Tìm khách có sẵn">
                <input
                  placeholder="Tên hoặc số điện thoại…"
                  value={customerSearch}
                  onKeyDown={(e) => {
                    if (e.key === "Enter") e.preventDefault();
                  }}
                  onChange={(e) => {
                    setCustomerSearch(e.target.value);
                    if (form.customer)
                      setForm({
                        ...form,
                        customer: "",
                        recipient_name: "",
                        phone: "",
                      });
                  }}
                />
              </Field>
              <Field label="Khách hàng có sẵn (tùy chọn)">
                <select
                  value={form.customer}
                  onChange={(e) => {
                    const c = customers.data?.results?.find(
                      (c) => String(c.id) === e.target.value,
                    );
                    setForm({
                      ...form,
                      customer: e.target.value,
                      recipient_name: c?.name || "",
                      phone: c?.phone || "",
                    });
                  }}
                >
                  <option value="">Nhập thông tin khách mới</option>
                  {customers.data?.results?.map((c) => (
                    <option key={c.id} value={c.id}>
                      {c.name}
                      {c.phone ? " — " + c.phone : ""}
                    </option>
                  ))}
                </select>
              </Field>
              <ErrorBox error={customers.error} />
              <Field label="Tên khách">
                <input
                  required
                  maxLength={150}
                  value={form.recipient_name}
                  onChange={(e) =>
                    setForm({ ...form, recipient_name: e.target.value })
                  }
                />
              </Field>
              <Field label="Điện thoại">
                <input
                  required
                  type="tel"
                  value={form.phone}
                  onChange={(e) => setForm({ ...form, phone: e.target.value })}
                />
              </Field>
              <Field label="Thanh toán">
                <select
                  value={form.payment_method}
                  onChange={(e) =>
                    setForm({ ...form, payment_method: e.target.value })
                  }
                >
                  <option value="CASH">Tiền mặt tại quầy</option>
                  <option value="BANK_TRANSFER">
                    Chuyển khoản xác nhận thủ công
                  </option>
                </select>
              </Field>
              <div className="pos-lines">
                {items.map((i) => (
                  <div key={i.variant}>
                    <span>{i.details.product_name}</span>
                    <input
                      aria-label="Số lượng"
                      required
                      type="number"
                      min="1"
                      max="1000"
                      value={i.quantity}
                      onChange={(e) => {
                        const quantity = Number(e.target.value);
                        if (
                          !Number.isSafeInteger(quantity) ||
                          quantity < 1 ||
                          quantity > 1000
                        )
                          return;
                        setItems(
                          items.map((x) =>
                            x.variant === i.variant
                              ? {
                                  ...x,
                                  quantity,
                                }
                              : x,
                          ),
                        );
                      }}
                    />
                    <button
                      aria-label="Bỏ sản phẩm"
                      type="button"
                      onClick={() =>
                        setItems(items.filter((x) => x.variant !== i.variant))
                      }
                    >
                      <Trash2 size={14} />
                    </button>
                  </div>
                ))}
              </div>
              <p className="print-total">{money(fromMinorUnits(sum))}</p>
              <button
                className="button primary"
                disabled={busy || !items.length}
              >
                {busy ? "Đang tạo…" : "Tạo đơn nháp"}
              </button>
            </form>
          </aside>
        </div>
      )}
    </>
  );
}
