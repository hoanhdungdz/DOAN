import React, { useRef, useState } from "react";
import { confirmAction } from "../../../shared/dialogs";
import { Link, useParams } from "react-router-dom";
import { Plus, Search, Eye, Pencil, X, Printer } from "lucide-react";
import { resources, labels, actionLabels } from "../features/resources/config";
import ResourceForm from "../features/resources/ResourceForm";
import StockReceiptDialog from "../features/resources/StockReceiptDialog";
import { useSession } from "../../../shared/session";
import {
  api,
  money,
  dateTime,
  errorText,
  operationKey,
} from "../../../shared/api";
import { Loading, Empty, ErrorBox, Pager, Badge } from "../../../shared/ui";
import useRemote from "../hooks/useRemote";
import StructuredData from "../../../shared/StructuredData";
import ProductRecordDetails from "../features/resources/ProductRecordDetails";
function cell(k, v) {
  if (v === null || v === undefined || v === "") return "—";
  if (typeof v === "boolean") return <Badge>{v ? "Có" : "Không"}</Badge>;
  if (["status", "kind"].includes(k)) return <Badge>{v}</Badge>;
  if (["price", "amount", "min_subtotal", "max_discount"].includes(k))
    return money(v);
  if (k === "discount_type") return v === "PERCENT" ? "Phần trăm" : "Số tiền";
  if (k.endsWith("_at") || k === "date_joined") return dateTime(v);
  if (Array.isArray(v)) return v.join(", ");
  return String(v);
}
function InventoryStoreFilter({ value, onChange, user }) {
  const remote = useRemote("stores/?page_size=100");
  return (
    <label className="inventory-store-filter">
      Chi nhánh
      <select
        aria-label="Lọc chi nhánh"
        value={value}
        disabled={remote.loading}
        onChange={(e) => onChange(e.target.value)}
      >
        <option value="">Tất cả chi nhánh được phép</option>
        {remote.data?.results
          ?.filter((store) => user.is_admin || user.stores.includes(store.id))
          .map((store) => (
            <option key={store.id} value={store.id}>
              {store.name}
            </option>
          ))}
      </select>
      <ErrorBox error={remote.error} />
    </label>
  );
}
export default function ResourcePage() {
  const { resource: name } = useParams(),
    config = resources[name],
    { user } = useSession(),
    [page, setPage] = useState(1),
    [search, setSearch] = useState(""),
    [revision, setRevision] = useState(0),
    [editing, setEditing] = useState(undefined),
    [detail, setDetail] = useState(null),
    [error, setError] = useState(""),
    [busy, setBusy] = useState(false),
    [low, setLow] = useState(false),
    [store, setStore] = useState(""),
    [receipt, setReceipt] = useState(null),
    [receiptNotice, setReceiptNotice] = useState(null),
    keys = useRef(new Map());
  const query = new URLSearchParams({
    page,
    search,
    internal: "true",
    ...(low ? { low: "true" } : {}),
    ...(store ? { store } : {}),
  });
  const remote = useRemote(`${name}/?${query}`, revision);
  if (!config) return <Empty text="Trang không tồn tại." />;
  const can = (permission) =>
      user.is_admin || user.permissions.includes(permission),
    writable = config.permission && can(config.permission),
    canCreate =
      writable &&
      !config.noCreate &&
      can(config.createPermission || config.permission);
  function saved() {
    setEditing(undefined);
    setRevision((r) => r + 1);
    setError("");
  }
  async function action(row, act) {
    if (
      !(await confirmAction(
        `${actionLabels[act]} ${name === "stock-transfers" ? "điều chuyển" : "chứng từ"} #${row.id}?`,
      ))
    )
      return;
    setBusy(true);
    setError("");
    try {
      await api(`${name}/${row.id}/${act}/`, { method: "POST", body: {} });
      saved();
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
          <span className="eyebrow">
            VẬN HÀNH / {config.title.toUpperCase()}
          </span>
          <h1>{config.title}</h1>
          <p className="subtle">
            {config.description ||
              "Quản lý dữ liệu trong phạm vi được cấp quyền."}
          </p>
        </div>
        {canCreate && (
          <button className="button primary" onClick={() => setEditing(null)}>
            <Plus size={16} />
            Tạo mới
          </button>
        )}
      </div>
      {receiptNotice && (
        <p className="notice">
          {receiptNotice.posted
            ? `Đã nhập thêm hàng theo phiếu #${receiptNotice.id}. Tồn kho đã được cập nhật.`
            : `Phiếu nhập #${receiptNotice.id} đang chờ kiểm tra ghi sổ.`}{" "}
          <Link to="/stock-documents">Xem chứng từ kho →</Link>
        </p>
      )}
      <div className="panel">
        <div className="toolbar">
          <div className="search-input">
            <Search size={15} />
            <input
              aria-label="Tìm trong danh sách"
              placeholder="Tìm kiếm…"
              value={search}
              onChange={(e) => {
                setSearch(e.target.value);
                setPage(1);
              }}
            />
          </div>
          {name === "inventory" && (
            <>
              <label className="filter-checkbox">
                <input
                  type="checkbox"
                  checked={low}
                  onChange={(e) => {
                    setLow(e.target.checked);
                    setPage(1);
                  }}
                />
                Cảnh báo tồn thấp
              </label>
              <InventoryStoreFilter
                value={store}
                user={user}
                onChange={(value) => {
                  setStore(value);
                  setPage(1);
                }}
              />
            </>
          )}
          <span className="toolbar-count">
            {remote.data?.count || 0} bản ghi
          </span>
        </div>
        <ErrorBox error={error || remote.error} />
        {remote.loading ? (
          <Loading />
        ) : remote.data?.results?.length ? (
          <div className="table-scroll">
            <table>
              <thead>
                <tr>
                  {config.columns.map((k) => (
                    <th key={k}>{labels[k] || k}</th>
                  ))}
                  <th>Thao tác</th>
                </tr>
              </thead>
              <tbody>
                {remote.data.results.map((row) => (
                  <tr key={row.id}>
                    {config.columns.map((k) => (
                      <td
                        className={k === "url" ? "truncate-cell" : ""}
                        key={k}
                      >
                        {cell(k, row[k])}
                      </td>
                    ))}
                    <td>
                      <div className="actions">
                        <button
                          aria-label="Xem chi tiết"
                          onClick={() => setDetail(row)}
                        >
                          <Eye size={14} />
                        </button>
                        {name === "invoices" && (
                          <Link
                            className="button"
                            aria-label={"Xem chứng từ " + row.code}
                            to={"/invoices/" + row.id}
                          >
                            <Printer size={14} />
                          </Link>
                        )}
                        {name === "customers" && (
                          <Link
                            className="button"
                            to={"/orders?customer=" + row.id}
                          >
                            Lịch sử
                          </Link>
                        )}
                        {["products", "variants", "inventory"].includes(name) &&
                          can("manage_stock") && (
                            <button
                              disabled={
                                name === "products" && !row.variants?.length
                              }
                              onClick={() => {
                                const variants =
                                  name === "products"
                                    ? row.variants
                                    : name === "variants"
                                      ? [row]
                                      : [
                                          {
                                            id: row.variant,
                                            sku: row.sku,
                                            product_name: row.product_name,
                                          },
                                        ];
                                setReceipt({
                                  variants,
                                  warehouse:
                                    name === "inventory" ? row.warehouse : "",
                                  productName: row.product_name || row.name,
                                });
                              }}
                            >
                              <Plus size={14} /> Nhập thêm hàng
                            </button>
                          )}
                        {writable &&
                          !config.noEdit &&
                          (!config.actions || row.status === "DRAFT") && (
                            <button
                              aria-label="Sửa bản ghi"
                              onClick={() => setEditing(row)}
                            >
                              <Pencil size={14} />
                            </button>
                          )}
                        {writable &&
                          config.actions?.[row.status]?.map((a) => (
                            <button
                              key={a}
                              disabled={busy}
                              onClick={() => action(row, a)}
                            >
                              {actionLabels[a]}
                            </button>
                          ))}
                        {writable && config.delete && (
                          <button
                            disabled={busy}
                            onClick={async () => {
                              if (
                                !(await confirmAction(
                                  name === "assignments"
                                    ? "Thu hồi phân công này?"
                                    : "Xóa bản ghi ảnh/thông số này?",
                                ))
                              )
                                return;
                              try {
                                await api(`${name}/${row.id}/`, {
                                  method: "DELETE",
                                });
                                saved();
                              } catch (e) {
                                setError(errorText(e));
                              }
                            }}
                          >
                            {name === "assignments" ? "Thu hồi" : "Xóa"}
                          </button>
                        )}
                      </div>
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
      </div>
      {editing !== undefined && (
        <ResourceForm
          key={name + String(editing?.id)}
          name={name}
          config={config}
          record={editing}
          onClose={() => setEditing(undefined)}
          onSaved={saved}
        />
      )}{" "}
      {receipt && (
        <StockReceiptDialog
          {...receipt}
          onClose={(id) => {
            setReceipt(null);
            if (id) setReceiptNotice({ id, posted: false });
          }}
          onReceived={(document) => {
            setReceipt(null);
            setReceiptNotice({ id: document.id, posted: true });
            setRevision((value) => value + 1);
          }}
        />
      )}
      {detail && (
        <div className="modal-backdrop">
          <section
            className="modal"
            role="dialog"
            aria-modal="true"
            aria-label="Chi tiết bản ghi"
          >
            <div className="modal-title">
              <h2>Chi tiết #{detail.id}</h2>
              <button aria-label="Đóng" onClick={() => setDetail(null)}>
                <X size={18} />
              </button>
            </div>
            <div className="record-details">
              {name === "products" ? (
                <ProductRecordDetails product={detail} />
              ) : (
                <StructuredData value={detail} labels={labels} />
              )}
            </div>
          </section>
        </div>
      )}
    </>
  );
}
