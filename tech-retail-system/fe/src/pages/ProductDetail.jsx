import React, { useState } from "react";
import { Link, useParams } from "react-router-dom";
import { ArrowLeft, ShoppingBag, MapPin, ShieldCheck } from "lucide-react";
import useRemote from "../hooks/useRemote";
import { useCart } from "../features/cart/CartContext";
import { money } from "../../../shared/api";
import { imageNote } from "../../../shared/productImages";
import ProductWarranty from "../components/ProductWarranty";
import ProductCommunity from "../components/ProductCommunity";
import { productWarranty, warrantyDescription } from "../../../shared/warranty";
import {
  Loading,
  ErrorBox,
  ProductImage,
  Field,
  Empty,
} from "../../../shared/ui";
export default function ProductDetail() {
  const { slug } = useParams(),
    { data: p, loading, error } = useRemote("products/" + slug + "/"),
    { add } = useCart();
  const [variant, setVariant] = useState(""),
    [store, setStore] = useState(""),
    [quantity, setQuantity] = useState(1),
    [busy, setBusy] = useState(false),
    [message, setMessage] = useState(""),
    [failure, setFailure] = useState("");
  if (loading) return <Loading />;
  if (error) return <ErrorBox error={error} />;
  if (!p) return <Empty />;
  const v =
      p.variants.find((v) => String(v.id) === variant) ||
      p.variants.find((v) => v.is_active),
    stock = v?.stock?.filter((s) => !store || String(s.store) === store) || [],
    available = stock.reduce((n, s) => n + s.available, 0);
  return (
    <main className="content-width detail">
      <Link to="/products" className="back-link">
        <ArrowLeft size={15} /> Tất cả sản phẩm
      </Link>
      <div className="detail-grid">
        <div>
          <div className="detail-visual">
            <ProductImage src={p.images?.[0]?.url} alt={p.name} />
            <span>{p.brand_name}</span>
          </div>
          {imageNote(p.images?.[0]?.url) && (
            <p className="notice image-note">{imageNote(p.images?.[0]?.url)}</p>
          )}
        </div>
        <section className="detail-info">
          <span className="eyebrow">
            {p.category_name} / {p.brand_name}
          </span>
          <h1>{p.name}</h1>
          <p className="sku">SKU: {v?.sku}</p>
          <strong className="detail-price">{money(v?.price)}</strong>
          <p className="subtle">{v?.condition}</p>
          <ProductWarranty key={v?.id} product={p} variant={v} />
          <div className="detail-options">
            <Field label="Biến thể">
              <select
                value={v?.id || ""}
                onChange={(e) => setVariant(e.target.value)}
              >
                {p.variants
                  .filter((v) => v.is_active)
                  .map((v) => (
                    <option key={v.id} value={v.id}>
                      {v.name} · {v.condition}
                    </option>
                  ))}
              </select>
            </Field>
            <Field label="Xem tồn tại chi nhánh">
              <select value={store} onChange={(e) => setStore(e.target.value)}>
                <option value="">Tất cả chi nhánh</option>
                {[...new Map(v?.stock?.map((s) => [s.store, s])).values()].map(
                  (s) => (
                    <option key={s.store} value={s.store}>
                      {s.store_name}
                    </option>
                  ),
                )}
              </select>
            </Field>
          </div>
          <div className="stock-list">
            {stock.map((s) => (
              <p key={s.warehouse}>
                <MapPin size={15} />
                <span>{s.store_name}</span>
                <b>{s.available} khả dụng</b>
              </p>
            ))}
          </div>
          <div className="add-cart">
            <input
              aria-label="Số lượng"
              type="number"
              min="1"
              max="1000"
              value={quantity}
              onChange={(e) => setQuantity(Number(e.target.value))}
            />
            <button
              className="button primary"
              disabled={busy || !v || available < quantity || quantity < 1}
              onClick={async () => {
                setBusy(true);
                setFailure("");
                try {
                  await add(v.id, quantity);
                  setMessage("Đã thêm vào giỏ hàng.");
                } catch (e) {
                  setFailure(e.message);
                } finally {
                  setBusy(false);
                }
              }}
            >
              <ShoppingBag size={18} />
              {busy ? "Đang thêm…" : "Thêm vào giỏ hàng"}
            </button>
          </div>
          {message && (
            <p className="notice">
              {message} <Link to="/cart">Xem giỏ hàng →</Link>
            </p>
          )}
          <ErrorBox error={failure} />
          <p className="fine">
            <ShieldCheck size={14} /> Giá và tồn kho sẽ được kiểm tra lại khi
            đặt hàng.
          </p>
        </section>
      </div>
      <ProductCommunity product={p}>
        <div className="detail-description">
          <section>
            <span className="eyebrow">THÔNG TIN THIẾT BỊ</span>
            <h2>Hiểu rõ lựa chọn của bạn.</h2>
            <p>{warrantyDescription(p.description, productWarranty(p, v))}</p>
          </section>
          <section className="panel product-specifications">
            <h3>Thông số kỹ thuật</h3>
            <table>
              <tbody>
                {p.specifications.map((s) => (
                  <tr key={s.id}>
                    <td>{s.name}</td>
                    <td>{s.value}</td>
                  </tr>
                ))}
              </tbody>
            </table>
            {!p.specifications.length && (
              <p>{p.raw_specs || "Chưa có thông số."}</p>
            )}
          </section>
        </div>
      </ProductCommunity>
    </main>
  );
}
