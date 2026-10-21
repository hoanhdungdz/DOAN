import React from "react";
import { useParams } from "react-router-dom";
import { Printer } from "lucide-react";
import { money, dateTime } from "../../../shared/api";
import { Loading, ErrorBox } from "../../../shared/ui";
import useRemote from "../hooks/useRemote";
export default function InvoicePage() {
  const { id } = useParams(),
    { data, loading, error } = useRemote(`invoices/${id}/`);
  if (loading) return <Loading />;
  if (error) return <ErrorBox error={error} />;
  const s = data.snapshot;
  return (
    <article className="invoice panel">
      <header>
        <div className="wordmark">
          tech<span>retail</span>
        </div>
        <h1>Chứng từ bán hàng</h1>
        <p>
          {data.code} · {dateTime(data.created_at)}
        </p>
        <p className="fine">
          Chứng từ phục vụ đồ án. Chưa tích hợp hóa đơn điện tử.
        </p>
        <button className="button no-print" onClick={() => window.print()}>
          <Printer size={16} /> In chứng từ
        </button>
      </header>
      <p>
        Chi nhánh: {s.store}
        <br />
        Đơn hàng: {s.code}
        <br />
        Khách hàng: {s.recipient_name}
        <br />
        Người bán: {s.seller || "Kênh online"}
      </p>
      <table>
        <thead>
          <tr>
            <th>Sản phẩm / SKU</th>
            <th>SL</th>
            <th>Đơn giá</th>
            <th>Thành tiền</th>
          </tr>
        </thead>
        <tbody>
          {s.items.map((i, k) => (
            <tr key={k}>
              <td>
                {i.name}
                <small className="cell-secondary">{i.sku}</small>
              </td>
              <td>{i.quantity}</td>
              <td>{money(i.unit_price)}</td>
              <td>{money(i.line_total)}</td>
            </tr>
          ))}
        </tbody>
      </table>
      {s.coupon_code && (
        <p>
          Tiền hàng: {money(s.subtotal)}
          <br />
          Mã {s.coupon_code}: −{money(s.discount_total)}
          <br />
          Phí giao hàng: {money(s.shipping_fee)}
        </p>
      )}
      <p className="print-total">Tổng cộng {money(s.total)}</p>
      <footer>In lại chứng từ không phát sinh thu tiền hoặc xuất kho.</footer>
    </article>
  );
}
