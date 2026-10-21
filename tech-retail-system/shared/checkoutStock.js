// Every cart line must be available in the same fulfillment warehouse.
export function checkoutWarehouses(warehouses, rows) {
  return warehouses.map((warehouse) => {
    const lines = rows.map((row) => {
      const stock = row.details?.stock?.find(
        (s) => Number(s.warehouse) === Number(warehouse.id),
      );
      const available = Math.max(0, Number(stock?.available) || 0);
      return {
        ...row,
        available,
        sufficient: Boolean(row.details) && available >= row.quantity,
      };
    });
    return {
      ...warehouse,
      lines,
      sufficient: lines.length > 0 && lines.every((line) => line.sufficient),
    };
  });
}

export function warehouseStockLabel(warehouse) {
  if (warehouse.sufficient) return `${warehouse.store_name} — Đủ hàng`;
  const missing = warehouse.lines.filter((line) => !line.sufficient);
  if (missing.some((line) => !line.details))
    return `${warehouse.store_name} — Có sản phẩm ngừng bán`;
  if (missing.every((line) => line.available === 0))
    return `${warehouse.store_name} — Hết hàng`;
  return `${warehouse.store_name} — Không đủ số lượng`;
}
