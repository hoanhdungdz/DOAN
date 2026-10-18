import React, { useEffect, useRef, useState } from "react";
import { confirmAction, promptReason } from "../../../shared/dialogs";
import { Link, useParams, useSearchParams } from "react-router-dom";
import { Plus, Printer, Search } from "lucide-react";
import {
  api,
  money,
  dateTime,
  errorText,
  operationKey,
} from "../../../shared/api";
import { useSession } from "../../../shared/session";
import {
  Loading,
  ErrorBox,
  Empty,
  Badge,
  Pager,
  Field,
} from "../../../shared/ui";
import { actionLabels } from "../features/resources/config";
import useRemote from "../hooks/useRemote";
export default function OrdersPage() {
  const { id } = useParams(),
    [params] = useSearchParams(),
    { user } = useSession(),
    [page, setPage] = useState(1),
    [search, setSearch] = useState(params.get("search") || ""),
    [status, setStatus] = useState(""),
    [revision, setRevision] = useState(0),
    [error, setError] = useState(""),
    [busy, setBusy] = useState(false),
    [reference, setReference] = useState(""),
    keys = useRef(new Map());
  const query = new URLSearchParams({
      page,
      search,
      status,
      ...(params.get("customer") ? { customer: params.get("customer") } : {}),
    }),
    remote = useRemote(id ? `orders/${id}/` : "orders/?" + query, revision),
    o = id ? remote.data : null;
  const sales = user.is_admin || user.permissions.includes("manage_sales"),
    payments = user.is_admin || user.permissions.includes("manage_payments");
  useEffect(() => {
    setSearch(params.get("search") || "");
    setPage(1);
  }, [params.get("search")]);
  const actions = {
    PENDING: ["confirm", "cancel"],
    CONFIRMED: ["pack", "cancel"],
    PACKING: ["ship", "cancel"],
    SHIPPED: ["complete"],
    DRAFT: ["finish", "cancel"],
  };
  async function operate(action) {
    const label = actionLabels[action];
    let reason = "";
    if (action === "cancel") {
      reason = await promptReason("Lý do hủy đơn:");
      if (!reason) return;
    } else if (!(await confirmAction(`${label} cho đơn ${o.code}?`))) return;
    setBusy(true);
    setError("");
    try {
      const body = { reason, reference };
      await api(`orders/${o.id}/${action}/`, {
        method: "POST",
        body,
        headers: {
          "Idempotency-Key": operationKey(keys.current, action + o.id, body),
        },
      });
      setRevision((r) => r + 1);
    } catch (e) {
      setError(errorText(e));
    } finally {
      setBusy(false);
    }
  }
  async function pay(kind) {
    if (
      !(await confirmAction(
        `${kind === "CAPTURE" ? "Xác nhận đã thu đủ" : "Xác nhận đã hoàn đủ"} ${money(o.grand_total)}?`,
      ))
    )
      return;
    setBusy(true);
    setError("");
    const body = { order: o.id, kind, reference };
    try {
      await api("payments/", {
        method: "POST",
        body,
        headers: {
          "Idempotency-Key": operationKey(keys.current, "payment", body),
        },
      });
      setRevision((r) => r + 1);
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
          <span className="eyebrow">BÁN HÀNG / ĐƠN HÀNG</span>
          <h1>{o ? o.code : "Đơn hàng"}</h1>
          <p className="subtle">
            Theo dõi và xử lý đơn trong phạm vi chi nhánh.
          </p>
        </div>
        {sales && (
          <Link to="/pos" className="button primary">
            <Plus size={16} /> Bán tại quầy
          </Link>
        )}
      </div>
      <ErrorBox error={error || remote.error} />
      {remote.loading ? (
        <Loading />
      ) : o ? (
        <>
          <div className="split">
            <section className="panel">
              <div className="order-detail-header">
                <Badge>{o.status}</Badge>
                <Badge>{o.payment_status}</Badge>
                <span className="subtle">{dateTime(o.created_at)}</span>
              </div>
              <div className="table-scroll">
                <table>
                  <thead>
                    <tr>
                      <th>Sản phẩm</th>
                      <th>SL</th>
                      <th>Đơn giá</th>
                      <th>Thành tiền</th>
                    </tr>
                  </thead>
                  <tbody>
                    {o.items.map((i) => (
                      <tr key={i.id}>
                        <td>
                          {i.name}
                          <small className="fine"> · {i.sku}</small>
                        </td>
                        <td>{i.quantity}</td>
                        <td>{money(i.unit_price)}</td>
                        <td>{money(i.line_total)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              <p className="print-total">{money(o.grand_total)}</p>
              <div className="actions">
                {sales &&
                  (actions[o.status] || []).map((action) => (
                    <button
                      disabled={busy}
                      key={action}
                      onClick={() => operate(action)}
                    >
                      {actionLabels[action]}
                    </button>
                  ))}
              </div>
            </section>
            <section className="panel">
              <h3>Thông tin đơn</h3>
              <p className="subtle">
                {o.recipient_name} · {o.phone}
                <br />
                {o.address || "Nhận tại cửa hàng"}
                <br />
                {o.store_name}
                <br />
                {o.channel} · {o.payment_method}
              </p>
              <Field label="Tham chiếu thu / hoàn tiền">
                <input
                  maxLength={200}
                  placeholder="Mã giao dịch hoặc biên nhận xác nhận"
                  value={reference}
                  onChange={(e) => setReference(e.target.value)}
                />
              </Field>
              <div className="actions">
                {payments &&
                  o.payment_status === "UNPAID" &&
                  o.status !== "DRAFT" &&
                  o.status !== "CANCELLED" && (
                    <button disabled={busy} onClick={() => pay("CAPTURE")}>
                      Xác nhận đã thu tiền
                    </button>
                  )}
                {payments && o.payment_status === "REFUND_PENDING" && (
                  <button disabled={busy} onClick={() => pay("REFUND")}>
                    Xác nhận đã hoàn tiền
                  </button>
                )}
                {o.status === "COMPLETED" && (
                  <Link to="/invoices" className="button">
                    <Printer size={15} /> Chứng từ
                  </Link>
                )}
              </div>
              <p className="fine">
                Xác nhận thủ công sau khi đã kiểm tra thu/hoàn thực tế. Không có
                đối soát ngân hàng tự động.
              </p>
            </section>
          </div>
          <section className="panel timeline">
            <h3>Lịch sử trạng thái</h3>
            {o.history.map((h) => (
              <div key={h.id}>
                <Badge>{h.status}</Badge>
                <span>{dateTime(h.created_at)}</span>
                <p>{h.reason || "—"}</p>
              </div>
            ))}
          </section>
        </>
      ) : (
        <section className="panel">
          <div className="toolbar">
            <div className="search-input">
              <Search size={15} />
              <input
                placeholder="Tìm mã đơn…"
                value={search}
                onChange={(e) => {
                  setSearch(e.target.value);
                  setPage(1);
                }}
              />
            </div>
            <select
              aria-label="Lọc trạng thái"
              value={status}
              onChange={(e) => {
                setStatus(e.target.value);
                setPage(1);
              }}
            >
              <option value="">Mọi trạng thái</option>
              {[
                "DRAFT",
                "PENDING",
                "CONFIRMED",
                "PACKING",
                "SHIPPED",
                "COMPLETED",
                "CANCELLED",
              ].map((s) => (
                <option key={s}>{s}</option>
              ))}
            </select>
          </div>
          {remote.data?.results?.length ? (
            <div className="table-scroll">
              <table>
                <thead>
                  <tr>
                    <th>Mã đơn</th>
                    <th>Khách hàng</th>
                    <th>Chi nhánh</th>
                    <th>Trạng thái</th>
                    <th>Thanh toán</th>
                    <th>Tổng tiền</th>
                    <th />
                  </tr>
                </thead>
                <tbody>
                  {remote.data.results.map((o) => (
                    <tr key={o.id}>
                      <td>
                        {o.code}
                        <small className="cell-secondary">
                          {dateTime(o.created_at)}
                        </small>
                      </td>
                      <td>{o.recipient_name}</td>
                      <td>{o.store_name}</td>
                      <td>
                        <Badge>{o.status}</Badge>
                      </td>
                      <td>
                        <Badge>{o.payment_status}</Badge>
                      </td>
                      <td>{money(o.grand_total)}</td>
                      <td>
                        <Link className="detail-link" to={"/orders/" + o.id}>
                          Chi tiết →
                        </Link>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            !remote.error && <Empty />
          )}
          {remote.data && (
            <Pager page={page} setPage={setPage} count={remote.data.count} />
          )}
        </section>
      )}
    </>
  );
}
