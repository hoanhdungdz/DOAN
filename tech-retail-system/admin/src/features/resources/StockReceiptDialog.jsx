import React, { useRef, useState } from "react";
import { Link } from "react-router-dom";
import { X } from "lucide-react";
import { api, errorText } from "../../../../shared/api";
import { ErrorBox, Field, Loading } from "../../../../shared/ui";
import useRemote from "../../hooks/useRemote";

export default function StockReceiptDialog({
  variants,
  warehouse = "",
  productName,
  onClose,
  onReceived,
}) {
  const remote = useRemote("warehouses/?scope=stock&page_size=100");
  const [form, setForm] = useState({
    warehouse: String(warehouse),
    variant: variants.length === 1 ? String(variants[0].id) : "",
    quantity: "1",
    reason: "",
  });
  const [documentId, setDocumentId] = useState(null),
    [error, setError] = useState(""),
    [busy, setBusy] = useState(false);
  const running = useRef(false);
  const warehouses = remote.data?.results || [];
  const set = (key, value) =>
    setForm((previous) => ({ ...previous, [key]: value }));
  async function receive(event) {
    event.preventDefault();
    if (running.current) return;
    if (
      !documentId &&
      (!warehouses.some((w) => w.id === Number(form.warehouse)) ||
        !variants.some((v) => v.id === Number(form.variant)) ||
        !Number.isSafeInteger(Number(form.quantity)) ||
        Number(form.quantity) <= 0 ||
        Number(form.quantity) > 100000 ||
        !form.reason.trim())
    ) {
      setError(
        "Chọn kho, biến thể, số lượng nguyên từ 1 đến 100.000 và nhập lý do nhập hàng.",
      );
      return;
    }
    running.current = true;
    setBusy(true);
    setError("");
    try {
      let id = documentId;
      if (!id) {
        const draft = await api("stock-documents/", {
          method: "POST",
          body: {
            warehouse: Number(form.warehouse),
            kind: "IN",
            reason: form.reason.trim(),
            items: [
              {
                variant: Number(form.variant),
                quantity: Number(form.quantity),
              },
            ],
          },
        });
        id = draft.id;
        setDocumentId(id);
      }
      // Retain this ID if the response is lost. Posting the same document is idempotent.
      const result = await api(`stock-documents/${id}/post/`, {
        method: "POST",
        body: {},
      });
      onReceived(result);
    } catch (e) {
      setError(errorText(e));
    } finally {
      running.current = false;
      setBusy(false);
    }
  }
  return (
    <div className="modal-backdrop">
      <section
        className="modal"
        role="dialog"
        aria-modal="true"
        aria-label="Nhập thêm hàng"
      >
        <div className="modal-title">
          <h2>Nhập thêm hàng</h2>
          <button
            type="button"
            aria-label="Đóng"
            disabled={busy}
            onClick={() => onClose(documentId)}
          >
            <X size={18} />
          </button>
        </div>
        <p>{productName}</p>
        <p className="subtle">
          Nhập số lượng bổ sung vào kho. Hệ thống tạo và ghi sổ phiếu nhập để
          lưu lịch sử; số lượng giữ chỗ không thay đổi.
        </p>
        <ErrorBox error={error || remote.error} />
        {documentId && (
          <p className="notice">
            Phiếu nhập #{documentId} đã được tạo. Nếu ghi sổ chưa được xác nhận,
            hãy thử lại cùng phiếu hoặc mở{" "}
            <Link to="/stock-documents">Chứng từ kho</Link> để kiểm tra.
          </p>
        )}
        {remote.loading ? (
          <Loading />
        ) : (
          <form onSubmit={receive}>
            <fieldset
              disabled={busy || Boolean(documentId)}
              className="receipt-fields form-grid"
            >
              <Field label="Kho nhận hàng">
                <select
                  required
                  value={form.warehouse}
                  onChange={(e) => set("warehouse", e.target.value)}
                >
                  <option value="">Chọn chi nhánh / kho</option>
                  {warehouses.map((w) => (
                    <option key={w.id} value={w.id}>
                      {w.store_name} — {w.name}
                    </option>
                  ))}
                </select>
              </Field>
              <Field label="Sản phẩm / biến thể">
                <select
                  required
                  value={form.variant}
                  onChange={(e) => set("variant", e.target.value)}
                >
                  <option value="">Chọn biến thể</option>
                  {variants.map((v) => (
                    <option key={v.id} value={v.id}>
                      {v.sku} — {v.product_name || productName}
                      {v.name && v.name !== "Mặc định" ? ` — ${v.name}` : ""}
                    </option>
                  ))}
                </select>
              </Field>
              <Field label="Số lượng nhập thêm">
                <input
                  type="number"
                  required
                  min="1"
                  max="100000"
                  step="1"
                  value={form.quantity}
                  onChange={(e) => set("quantity", e.target.value)}
                />
              </Field>
              <Field label="Lý do nhập hàng">
                <input
                  required
                  maxLength={500}
                  value={form.reason}
                  onChange={(e) => set("reason", e.target.value)}
                  placeholder="Ví dụ: Nhập bổ sung từ nhà cung cấp"
                />
              </Field>
            </fieldset>
            <div className="actions">
              <button
                type="button"
                disabled={busy}
                onClick={() => onClose(documentId)}
              >
                Đóng
              </button>
              <button
                className="button primary"
                disabled={busy || Boolean(remote.error) || !warehouses.length}
              >
                {busy
                  ? "Đang ghi nhận…"
                  : documentId
                    ? `Thử ghi sổ phiếu #${documentId}`
                    : "Xác nhận nhập kho"}
              </button>
            </div>
          </form>
        )}
      </section>
    </div>
  );
}
