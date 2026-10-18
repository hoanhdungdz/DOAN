import React, { useEffect, useRef, useState } from "react";
import { X, Plus, Trash2 } from "lucide-react";
import { api, all, errorText, operationKey } from "../../../../shared/api";
import { Field, ErrorBox, Loading } from "../../../../shared/ui";
import { useSession } from "../../../../shared/session";
function labelFor(r) {
  return r.product_name
    ? `${r.sku} — ${r.product_name}`
    : r.code
      ? `${r.code}${r.recipient_name ? " — " + r.recipient_name : ""}`
      : r.full_name
        ? `${r.full_name} (${r.email})`
        : r.store_name
          ? `${r.store_name} — ${r.name}`
          : r.name || r.email || String(r.id);
}
export default function ResourceForm({
  name,
  config,
  record,
  onClose,
  onSaved,
}) {
  const { user } = useSession(),
    [form, setForm] = useState(() =>
      Object.fromEntries(
        config.fields.map((f) => [
          f.name,
          record?.[f.name] ??
            f.default ??
            (f.type === "boolean"
              ? true
              : f.type === "items"
                ? []
                : f.type === "multiselect"
                  ? []
                  : ""),
        ]),
      ),
    ),
    [options, setOptions] = useState({}),
    [loading, setLoading] = useState(true),
    [error, setError] = useState(""),
    [busy, setBusy] = useState(false),
    keys = useRef(new Map());
  const fields = config.fields.filter(
    (f) =>
      !(record && name === "employees" && !user.is_admin && f.name === "user"),
  );
  useEffect(() => {
    let live = true;
    const sources = [
      ...new Set(fields.filter((f) => f.source).map((f) => f.source)),
      ...(fields.some((f) => f.type === "items") ? ["variants/"] : []),
    ];
    Promise.all(
      sources.map(async (s) => [
        s,
        await all(
          s +
            (user.is_admin
              ? (s.includes("?") ? "&" : "?") + "internal=true"
              : ""),
        ),
      ]),
    )
      .then(async (d) => {
        const loaded = Object.fromEntries(d);
        if (fields.some((f) => f.type === "items")) {
          const balances = await all("inventory/");
          const choices = new Map(
            (loaded["variants/"] || []).map((v) => [v.id, v]),
          );
          for (const b of balances)
            if (!choices.has(b.variant))
              choices.set(b.variant, {
                id: b.variant,
                sku: b.sku,
                product_name: b.product_name,
              });
          loaded["variants/"] = [...choices.values()];
        }
        if (live) setOptions(loaded);
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
  }, []);
  function set(k, v) {
    setForm((f) => ({ ...f, [k]: v }));
  }
  async function save(e) {
    e.preventDefault();
    setBusy(true);
    setError("");
    try {
      const body = {};
      for (const f of fields) {
        const v = form[f.name];
        if (f.optionalOnEdit && record && !v) continue;
        if (f.type === "number")
          body[f.name] =
            v === "" ? null : f.name === "price" ? String(v) : Number(v);
        else if (f.type === "select")
          body[f.name] = v === "" ? null : f.source ? Number(v) : v;
        else if (f.type === "items")
          body[f.name] = v.map((r) => ({
            variant: Number(r.variant),
            quantity: Number(r.quantity),
          }));
        else body[f.name] = v;
      }
      const id = name === "products" ? record?.slug : record?.id;
      await api(`${name}/${record ? id + "/" : ""}`, {
        method: record ? "PATCH" : "POST",
        body,
        headers:
          name === "payments"
            ? { "Idempotency-Key": operationKey(keys.current, "payment", body) }
            : {},
      });
      onSaved();
    } catch (e) {
      setError(errorText(e));
    } finally {
      setBusy(false);
    }
  }
  return (
    <div className="modal-backdrop">
      <section
        className="modal"
        role="dialog"
        aria-modal="true"
        aria-label={config.title}
      >
        <div className="modal-title">
          <h2>
            {record ? "Cập nhật" : "Tạo mới"} · {config.title}
          </h2>
          <button onClick={onClose} aria-label="Đóng">
            <X size={18} />
          </button>
        </div>
        <ErrorBox error={error} />
        {loading ? (
          <Loading />
        ) : (
          <form onSubmit={save}>
            <div className="form-grid">
              {fields.map((f) => (
                <div
                  key={f.name}
                  className={
                    ["items", "textarea", "multiselect"].includes(f.type)
                      ? "wide"
                      : ""
                  }
                >
                  <Field label={f.label}>
                    {f.type === "boolean" ? (
                      <select
                        value={String(form[f.name])}
                        onChange={(e) => set(f.name, e.target.value === "true")}
                      >
                        <option value="true">Có</option>
                        <option value="false">Không</option>
                      </select>
                    ) : f.type === "select" || f.type === "multiselect" ? (
                      <select
                        required={!f.optional}
                        multiple={f.type === "multiselect"}
                        size={f.type === "multiselect" ? 8 : undefined}
                        value={form[f.name]}
                        onChange={(e) =>
                          set(
                            f.name,
                            f.type === "multiselect"
                              ? [...e.target.selectedOptions].map((x) =>
                                  Number(x.value),
                                )
                              : e.target.value,
                          )
                        }
                      >
                        {f.type !== "multiselect" && (
                          <option value="">
                            {f.optional ? "Không chọn" : "Chọn giá trị"}
                          </option>
                        )}
                        {f.options?.map(([id, label]) => (
                          <option key={id} value={id}>
                            {label}
                          </option>
                        ))}
                        {f.source &&
                          options[f.source]?.map((r) => (
                            <option key={r.id} value={r.id}>
                              {labelFor(r)}
                            </option>
                          ))}
                      </select>
                    ) : f.type === "textarea" ? (
                      <textarea
                        required={!f.optional}
                        value={form[f.name]}
                        onChange={(e) => set(f.name, e.target.value)}
                      />
                    ) : f.type === "items" ? (
                      <div>
                        {form.items.map((r, i) => (
                          <div className="line-row" key={i}>
                            <select
                              aria-label="Sản phẩm"
                              required
                              value={r.variant}
                              onChange={(e) =>
                                set(
                                  "items",
                                  form.items.map((row, j) =>
                                    j === i
                                      ? { ...row, variant: e.target.value }
                                      : row,
                                  ),
                                )
                              }
                            >
                              <option value="">Chọn sản phẩm / SKU</option>
                              {options["variants/"]?.map((v) => (
                                <option key={v.id} value={v.id}>
                                  {labelFor(v)}
                                </option>
                              ))}
                            </select>
                            <input
                              aria-label="Số lượng"
                              required
                              type="number"
                              value={r.quantity}
                              min={form.kind === "ADJUST" ? undefined : 1}
                              onChange={(e) =>
                                set(
                                  "items",
                                  form.items.map((row, j) =>
                                    j === i
                                      ? { ...row, quantity: e.target.value }
                                      : row,
                                  ),
                                )
                              }
                            />
                            <button
                              type="button"
                              aria-label="Xóa dòng"
                              onClick={() =>
                                set(
                                  "items",
                                  form.items.filter((_, j) => j !== i),
                                )
                              }
                            >
                              <Trash2 size={14} />
                            </button>
                          </div>
                        ))}
                        <button
                          type="button"
                          className="button"
                          onClick={() =>
                            set("items", [
                              ...form.items,
                              { variant: "", quantity: 1 },
                            ])
                          }
                        >
                          <Plus size={15} /> Thêm dòng
                        </button>
                        <p className="fine">
                          Điều chỉnh nhập delta có dấu. Nhận điều chuyển hiện
                          tại yêu cầu nhận đủ toàn bộ.
                        </p>
                      </div>
                    ) : (
                      <input
                        type={f.type}
                        required={!f.optional && !(f.optionalOnEdit && record)}
                        min={f.min}
                        step={f.type === "number" ? "any" : undefined}
                        autoComplete={
                          f.type === "password" ? "new-password" : undefined
                        }
                        value={form[f.name] ?? ""}
                        onChange={(e) => set(f.name, e.target.value)}
                      />
                    )}
                  </Field>
                </div>
              ))}
            </div>
            <div className="actions">
              <button type="button" onClick={onClose}>
                Đóng
              </button>
              <button className="button primary" disabled={busy}>
                {busy ? "Đang lưu…" : "Lưu dữ liệu"}
              </button>
            </div>
          </form>
        )}
      </section>
    </div>
  );
}
