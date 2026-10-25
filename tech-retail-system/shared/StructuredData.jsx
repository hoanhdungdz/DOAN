import React from "react";
import { money, dateTime } from "./api";
import "./StructuredData.css";

const names = {
  id: "Mã",
  name: "Tên",
  title: "Tiêu đề",
  value: "Giá trị",
  unit: "Đơn vị",
  description: "Mô tả",
  raw_specs: "Thông số gốc",
  specifications: "Thông số kỹ thuật",
  variants: "Biến thể và giá",
  attributes: "Thuộc tính",
  stock: "Tồn kho theo chi nhánh",
  sku: "SKU",
  price: "Giá bán",
  condition: "Tình trạng",
  warranty_months: "Bảo hành (tháng)",
  is_active: "Đang hoạt động",
  category: "Mã danh mục",
  category_name: "Danh mục",
  brand: "Mã hãng",
  brand_name: "Thương hiệu",
  images: "Hình ảnh",
  url: "Đường dẫn ảnh",
  display_order: "Thứ tự hiển thị",
  slug: "Đường dẫn sản phẩm",
  source_namespace: "Nguồn dữ liệu",
  source_id: "Mã dữ liệu nguồn",
  source_url: "Đường dẫn nguồn",
  original_slug: "Đường dẫn gốc",
  created_at: "Ngày tạo",
  updated_at: "Cập nhật lần cuối",
  product: "Mã sản phẩm",
  product_name: "Sản phẩm",
  store: "Mã chi nhánh",
  store_name: "Chi nhánh",
  warehouse: "Mã kho",
  warehouse_name: "Kho",
  on_hand: "Tồn thực tế",
  reserved: "Đang giữ",
  available: "Khả dụng",
  items: "Danh sách hàng",
  quantity: "Số lượng",
  numeric_value: "Giá trị số",
  source_label: "Kho nguồn",
  destination_label: "Kho đích",
};
export function readableKey(key, labels = {}) {
  return Object.hasOwn(labels, key)
    ? labels[key]
    : Object.hasOwn(names, key)
      ? names[key]
      : key.replaceAll("_", " ");
}
export function parseStructured(value) {
  if (typeof value !== "string" || !/^[\s]*[\[{]/.test(value)) return value;
  try {
    return JSON.parse(value);
  } catch {
    return value;
  }
}

export default function StructuredData({
  value,
  field = "",
  labels = {},
  depth = 0,
}) {
  const data = parseStructured(value);
  if (data === null || data === undefined || data === "")
    return <span className="subtle">Chưa có dữ liệu</span>;
  if (depth > 12)
    return <span className="subtle">Dữ liệu có quá nhiều cấp.</span>;
  if (Array.isArray(data))
    return data.length ? (
      <ul className="structured-array">
        {data.map((item, index) => (
          <li key={index}>
            <StructuredData value={item} labels={labels} depth={depth + 1} />
          </li>
        ))}
      </ul>
    ) : (
      <span className="subtle">Chưa có dữ liệu</span>
    );
  if (typeof data === "object")
    return Object.keys(data).length ? (
      <dl className="structured-data">
        {Object.entries(data).map(([key, item]) => (
          <div className="structured-row" key={key}>
            <dt>{readableKey(key, labels)}</dt>
            <dd>
              <StructuredData
                value={item}
                field={key}
                labels={labels}
                depth={depth + 1}
              />
            </dd>
          </div>
        ))}
      </dl>
    ) : (
      <span className="subtle">Chưa có dữ liệu</span>
    );
  if (typeof data === "boolean") return <span>{data ? "Có" : "Không"}</span>;
  if (
    ["price", "amount", "subtotal", "grand_total", "discount_total"].includes(
      field,
    )
  )
    return <span>{money(data)}</span>;
  if (field.endsWith("_at") && !Number.isNaN(new Date(data).getTime()))
    return <span>{dateTime(data)}</span>;
  return <span className="structured-text">{String(data)}</span>;
}
