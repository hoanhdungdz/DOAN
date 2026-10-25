import React from "react";
import { money } from "../../../../shared/api";
import { Badge, ProductImage } from "../../../../shared/ui";
import StructuredData from "../../../../shared/StructuredData";

export default function ProductRecordDetails({ product }) {
  return (
    <div className="product-record-detail">
      <header>
        <h3>{product.name}</h3>
        <Badge>{product.is_active ? "Đang hiển thị" : "Đã ẩn"}</Badge>
      </header>
      <StructuredData
        value={{
          category_name: product.category_name,
          brand_name: product.brand_name,
        }}
      />
      {!!product.images?.length && (
        <div className="product-record-images">
          {product.images.map((image) => (
            <ProductImage
              key={image.id || image.url}
              src={image.url}
              alt={product.name}
            />
          ))}
        </div>
      )}
      <section>
        <h4>Mô tả sản phẩm</h4>
        <StructuredData value={product.description} />
      </section>
      <section>
        <h4>Biến thể và giá bán</h4>
        <div className="table-scroll">
          <table>
            <thead>
              <tr>
                <th>SKU / biến thể</th>
                <th>Giá bán</th>
                <th>Tình trạng</th>
                <th>Bảo hành</th>
              </tr>
            </thead>
            <tbody>
              {product.variants?.map((variant) => (
                <tr key={variant.id}>
                  <td>
                    <strong>{variant.sku}</strong>
                    <br />
                    {variant.name}
                  </td>
                  <td>{money(variant.price)}</td>
                  <td>
                    {variant.condition}
                    {!variant.is_active && <small> · Ngừng bán</small>}
                  </td>
                  <td>{variant.warranty_months} tháng</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        {!product.variants?.length && (
          <p className="subtle">Chưa có biến thể.</p>
        )}
        {product.variants?.map((variant) => (
          <div key={variant.id} className="product-variant-stock">
            <h5>{variant.sku} · Tồn theo chi nhánh</h5>
            {variant.stock?.length ? (
              <ul>
                {variant.stock.map((stock) => (
                  <li key={stock.warehouse}>
                    <span>
                      {stock.store_name ||
                        stock.warehouse_name ||
                        `Kho #${stock.warehouse}`}
                    </span>
                    <strong>{stock.available} khả dụng</strong>
                  </li>
                ))}
              </ul>
            ) : (
              <p className="subtle">Chưa có thông tin tồn kho.</p>
            )}
            {variant.attributes &&
              Object.keys(variant.attributes).length > 0 && (
                <StructuredData value={variant.attributes} />
              )}
          </div>
        ))}
      </section>
      <section>
        <h4>Thông số kỹ thuật</h4>
        {product.specifications?.length ? (
          <table>
            <tbody>
              {product.specifications.map((spec) => (
                <tr key={spec.id}>
                  <th>{spec.name}</th>
                  <td>
                    <StructuredData value={spec.value} />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        ) : (
          <StructuredData value={product.raw_specs} />
        )}
      </section>
      <details>
        <summary>Thông tin dữ liệu nguồn</summary>
        <StructuredData
          value={{
            id: product.id,
            slug: product.slug,
            source_namespace: product.source_namespace,
            source_id: product.source_id,
            source_url: product.source_url,
            created_at: product.created_at,
            updated_at: product.updated_at,
          }}
        />
      </details>
    </div>
  );
}
