import React, { useState } from "react";
import { Link } from "react-router-dom";
import { Plus, Check } from "lucide-react";
import { money } from "../../../shared/api";
import { ProductImage } from "../../../shared/ui";
import { useCart } from "../features/cart/CartContext";
export default function ProductCard({ product }) {
  const v = product.variants?.find((x) => x.is_active),
    { add } = useCart(),
    [busy, setBusy] = useState(false),
    [added, setAdded] = useState(false),
    [error, setError] = useState("");
  const available = v?.stock?.reduce((n, s) => n + s.available, 0) || 0;
  async function put() {
    if (!v) return;
    setBusy(true);
    try {
      await add(v.id);
      setAdded(true);
      setTimeout(() => setAdded(false), 1600);
    } catch (e) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  }
  return (
    <article className="product-card">
      <Link to={`/products/${product.slug}`} className="product-visual">
        <span className="product-brand">{product.brand_name}</span>
        <ProductImage
          src={product.images?.[0]?.url}
          alt={product.name}
          loading="lazy"
        />
        <span className="product-condition">{v?.condition}</span>
      </Link>
      <div className="product-info">
        <small>{product.category_name}</small>
        <Link to={`/products/${product.slug}`}>
          <h3>{product.name}</h3>
        </Link>
        <div className="product-bottom">
          <div>
            <strong>{money(v?.price)}</strong>
            <span className={available ? "availability" : "availability out"}>
              {available ? "Có hàng" : "Tạm hết hàng"}
            </span>
          </div>
          <button
            aria-label={`Thêm ${product.name} vào giỏ`}
            disabled={!v || !available || busy}
            onClick={put}
          >
            {added ? <Check size={17} /> : <Plus size={17} />}
          </button>
        </div>
        {error && <p className="error">{error}</p>}
      </div>
    </article>
  );
}
