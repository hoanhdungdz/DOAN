import React, { useState, useEffect } from "react";
import { Link, useSearchParams } from "react-router-dom";
import {
  ArrowUpRight,
  SlidersHorizontal,
  ArrowRight,
  ShieldCheck,
  Truck,
  Layers,
  MapPin,
} from "lucide-react";
import useRemote from "../hooks/useRemote";
import ProductCard from "../components/ProductCard";
import {
  Loading,
  ErrorBox,
  Empty,
  Pager,
  ProductImage,
} from "../../../shared/ui";
import { money, all, errorText } from "../../../shared/api";
import SearchSelect from "../../../shared/SearchSelect";
export default function CatalogPage({ home = false }) {
  const [params, setParams] = useSearchParams(),
    [page, setPage] = useState(1),
    [filtersOpen, setFiltersOpen] = useState(false),
    [brands, setBrands] = useState({ data: null, loading: true, error: "" });
  const query = new URLSearchParams(params);
  query.set("page", page);
  if (home && !params.toString()) query.set("page_size", "8");
  const size = home && !params.toString() ? 8 : 20;
  const products = useRemote("products/?" + query),
    categories = useRemote("categories/?page_size=100"),
    stores = useRemote("stores/?page_size=100");
  useEffect(() => {
    let live = true;
    all("brands/")
      .then((results) => {
        if (live) setBrands({ data: { results }, loading: false, error: "" });
      })
      .catch((error) => {
        if (live)
          setBrands({ data: null, loading: false, error: errorText(error) });
      });
    return () => {
      live = false;
    };
  }, []);
  useEffect(() => setPage(1), [params.toString()]);
  function filter(k, v) {
    const q = new URLSearchParams(params);
    if (v) q.set(k, v);
    else q.delete(k);
    setParams(q);
  }
  const selected = categories.data?.results?.find(
    (x) => String(x.id) === params.get("category"),
  );
  const hero = products.data?.results?.[0];
  return (
    <main className="catalog-page">
      {home && !params.toString() && (
        <>
          <section className="hero">
            <div className="hero-copy">
              <span className="eyebrow">
                <i /> KHÁM PHÁ THẾ GIỚI CÔNG NGHỆ
              </span>
              <h1>
                Đúng thiết bị.
                <br />
                <em>Mở khả năng.</em>
              </h1>
              <p>
                Từ công việc đến những phút giây của riêng bạn.
                <br />
                Tìm thiết bị phù hợp cho mỗi ngày.
              </p>
              <Link to="/products" className="button light">
                Khám phá sản phẩm <ArrowUpRight size={18} />
              </Link>
              <div className="hero-caption">
                <span>01 — THIẾT BỊ CHO BẠN</span>
                <div className="hero-line" />
              </div>
            </div>
            <div className="hero-art">
              <div className="orbit orbit-one" />
              <div className="orbit orbit-two" />
              <span className="hero-dot" />
              {hero && (
                <>
                  <ProductImage src={hero.images?.[0]?.url} alt={hero.name} />
                  <Link to={"/products/" + hero.slug} className="hero-product">
                    <div>
                      <small>TRONG BỘ SƯU TẬP</small>
                      <strong>{hero.name}</strong>
                      <span>{money(hero.variants?.[0]?.price)}</span>
                    </div>
                    <ArrowUpRight size={23} />
                  </Link>
                </>
              )}
              <span className="hero-side">
                SELECTED TECHNOLOGY / EVERYDAY POSSIBILITIES
              </span>
            </div>
          </section>
          <div className="benefits">
            <span>
              <ShieldCheck size={18} /> Thông tin sản phẩm rõ ràng
            </span>
            <span>
              <MapPin size={18} /> Kiểm tra tồn theo chi nhánh
            </span>
            <span>
              <Truck size={18} /> Đặt hàng online & nhận tại cửa hàng
            </span>
          </div>
        </>
      )}
      <div className="category-strip">
        <Link
          className={!params.get("category") ? "active" : ""}
          to="/products"
        >
          Tất cả thiết bị <Layers size={16} />
        </Link>
        {categories.data?.results?.map((c) => (
          <button
            key={c.id}
            className={params.get("category") === String(c.id) ? "active" : ""}
            onClick={() => filter("category", String(c.id))}
          >
            {c.name}
            <ArrowUpRight size={13} />
          </button>
        ))}
      </div>
      <section className="collection">
        <div className="collection-heading">
          <div>
            <span className="eyebrow">CHỌN THIẾT BỊ TIẾP THEO CỦA BẠN</span>
            <h2>
              {selected?.name || "Một thế giới để khám phá."}
              <sup>{products.data?.count || 0}</sup>
            </h2>
          </div>
          <button
            className="filter-toggle"
            onClick={() => setFiltersOpen(!filtersOpen)}
          >
            <SlidersHorizontal size={17} /> Bộ lọc
          </button>
        </div>
        <div className={`catalog-layout ${filtersOpen ? "filters-open" : ""}`}>
          <aside className="filter-panel">
            <div className="filter-title">
              Lọc sản phẩm <SlidersHorizontal size={15} />
            </div>
            <div className="filter-brand">
              <span>Thương hiệu</span>
              <SearchSelect
                label="Thương hiệu"
                placeholder="Nhập tên hãng…"
                emptyLabel="Tất cả thương hiệu"
                disabled={brands.loading}
                value={params.get("brand") || ""}
                options={(brands.data?.results || []).map((brand) => ({
                  value: brand.id,
                  label: brand.name,
                }))}
                onChange={(value) => filter("brand", value)}
              />
            </div>
            <label>
              Khoảng giá
              <input
                aria-label="Giá tối thiểu"
                type="number"
                min="0"
                placeholder="Từ (VND)"
                value={params.get("price_min") || ""}
                onChange={(e) => filter("price_min", e.target.value)}
              />
              <input
                aria-label="Giá tối đa"
                type="number"
                min="0"
                placeholder="Đến (VND)"
                value={params.get("price_max") || ""}
                onChange={(e) => filter("price_max", e.target.value)}
              />
            </label>
            <label>
              Chi nhánh
              <select
                value={params.get("store") || ""}
                onChange={(e) => filter("store", e.target.value)}
              >
                <option value="">Toàn bộ chi nhánh</option>
                {stores.data?.results?.map((s) => (
                  <option key={s.id} value={s.id}>
                    {s.name}
                  </option>
                ))}
              </select>
            </label>
            <label>
              Tình trạng
              <select
                value={params.get("condition") || ""}
                onChange={(e) => filter("condition", e.target.value)}
              >
                <option value="">Tất cả tình trạng</option>
                {[
                  "Mới 100% (Chính hãng)",
                  "Đã kích hoạt",
                  "Cũ đẹp (Like New)",
                  "Đã qua sử dụng",
                  "Cũ trầy xước",
                  "Đổi bảo hành",
                ].map((c) => (
                  <option key={c}>{c}</option>
                ))}
              </select>
            </label>
            <label>
              Thông số cần tìm
              <input
                placeholder="Ví dụ: 16GB, OLED…"
                value={params.get("spec") || ""}
                onChange={(e) => filter("spec", e.target.value)}
              />
            </label>
            <label className="checkbox">
              <input
                type="checkbox"
                checked={params.get("in_stock") === "true"}
                onChange={(e) =>
                  filter("in_stock", e.target.checked ? "true" : "")
                }
              />
              Chỉ thiết bị còn hàng
            </label>
            {params.toString() && (
              <button className="clear-filters" onClick={() => setParams({})}>
                Xóa bộ lọc
              </button>
            )}
            <div className="filter-note">
              <span>CHỌN THEO CÁCH CỦA BẠN</span>
              <p>
                Thông số, tình trạng và tồn kho được hiển thị trên từng sản
                phẩm.
              </p>
              <ArrowUpRight size={25} />
            </div>
          </aside>
          <div>
            <div className="results-bar">
              <span>
                {params.get("search")
                  ? `Kết quả cho “${params.get("search")}”`
                  : "Thiết bị được chọn từ catalog"}
                <b> · {products.data?.count || 0} sản phẩm</b>
              </span>
              <select
                aria-label="Sắp xếp"
                value={params.get("sort") || "name"}
                onChange={(e) => filter("sort", e.target.value)}
              >
                <option value="name">Theo tên sản phẩm</option>
                <option value="price">Giá thấp đến cao</option>
                <option value="-price">Giá cao đến thấp</option>
              </select>
            </div>
            <ErrorBox
              error={
                products.error ||
                categories.error ||
                brands.error ||
                stores.error
              }
            />
            {products.loading ? (
              <Loading />
            ) : products.data?.results?.length ? (
              <div className="products-grid">
                {products.data.results.map((p) => (
                  <ProductCard key={p.id} product={p} />
                ))}
              </div>
            ) : (
              !products.error && (
                <Empty text="Không tìm thấy thiết bị phù hợp. Hãy thử thay đổi bộ lọc." />
              )
            )}
            {products.data && (
              <Pager
                page={page}
                setPage={setPage}
                count={products.data.count}
                size={size}
              />
            )}
          </div>
        </div>
      </section>
    </main>
  );
}
