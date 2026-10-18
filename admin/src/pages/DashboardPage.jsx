import React, { useState } from "react";
import { Link } from "react-router-dom";
import {
  ArrowUpRight,
  Download,
  TrendingUp,
  Package,
  Wallet,
  ShoppingBag,
} from "lucide-react";
import { useSession } from "../../../shared/session";
import { money } from "../../../shared/api";
import { Loading, ErrorBox, Empty, Badge } from "../../../shared/ui";
import useRemote from "../hooks/useRemote";
export default function DashboardPage({ report = false }) {
  const { user } = useSession(),
    canReport = user.is_admin || user.permissions.includes("view_reports"),
    canStock = user.is_admin || user.permissions.includes("manage_stock");
  const [filters, setFilters] = useState({ start: "", end: "", store: "" });
  const query = new URLSearchParams(
    Object.entries(filters).filter(([, v]) => v),
  );
  const remote = useRemote(
    canReport
      ? "reports/summary/?" + query
      : canStock
        ? "reports/inventory/?" + query
        : "orders/?page_size=5",
  );
  const stores = useRemote(
    "stores/?page_size=100&scope=" +
      (canReport ? "reports" : canStock ? "stock" : "sales"),
  );
  const d = remote.data;
  return (
    <>
      <div className="page-title">
        <div>
          <span className="eyebrow">
            {report ? "PHÂN TÍCH / BÁO CÁO" : "TECH RETAIL / TỔNG QUAN"}
          </span>
          <h1>
            {report ? "Báo cáo kinh doanh" : `Một ngày vận hành rõ ràng.`}
          </h1>
          <p className="subtle">
            {report
              ? "Doanh thu đơn hoàn tất đã thu tiền; giao dịch hoàn theo ngày hoàn."
              : `Xin chào ${user.full_name || user.email}. Dữ liệu được giới hạn theo quyền của bạn.`}
          </p>
        </div>
        {canReport && (
          <a href={"/api/v1/reports/export/?" + query} className="button">
            <Download size={15} /> Xuất CSV
          </a>
        )}
      </div>
      {canReport || canStock ? (
        <div className="toolbar report-filters">
          <label>
            Từ ngày
            <input
              type="date"
              value={filters.start}
              onChange={(e) =>
                setFilters({ ...filters, start: e.target.value })
              }
            />
          </label>
          <label>
            Đến ngày
            <input
              type="date"
              value={filters.end}
              onChange={(e) => setFilters({ ...filters, end: e.target.value })}
            />
          </label>
          <label>
            Chi nhánh
            <select
              value={filters.store}
              onChange={(e) =>
                setFilters({ ...filters, store: e.target.value })
              }
            >
              <option value="">Phạm vi được cấp quyền</option>
              {stores.data?.results
                ?.filter((s) => user.stores.includes(s.id))
                .map((s) => (
                  <option value={s.id} key={s.id}>
                    {s.name}
                  </option>
                ))}
            </select>
          </label>
        </div>
      ) : null}
      <ErrorBox error={remote.error} />
      {remote.loading ? (
        <Loading />
      ) : d && canReport ? (
        <>
          <div className="metric-grid">
            {[
              ["Doanh thu bán ròng", money(d.sales_net), TrendingUp],
              ["Thu tiền ròng", money(d.cash_net), Wallet],
              ["Đơn hoàn tất", d.completed_orders, ShoppingBag],
              ["Tồn khả dụng", d.stock.available, Package],
            ].map(([label, value, Icon]) => (
              <section key={label} className="metric">
                <div>
                  <small>{label}</small>
                  <Icon size={17} />
                </div>
                <strong>{value}</strong>
                <span className="fine">Trong phạm vi và thời gian chọn</span>
              </section>
            ))}
          </div>
          <div className="dashboard-grid">
            <section className="panel">
              <div className="panel-heading">
                <h3>Doanh thu theo ngày</h3>
                <span className="fine">Giờ Việt Nam</span>
              </div>
              {d.daily.length ? (
                <div className="revenue-chart">
                  {d.daily.map((row) => (
                    <div key={row.day}>
                      <span>{row.day}</span>
                      <div>
                        <i
                          style={{
                            width:
                              Math.max(
                                1,
                                (Number(row.revenue) /
                                  Math.max(
                                    ...d.daily.map((x) => Number(x.revenue)),
                                  )) *
                                  100,
                              ) + "%",
                          }}
                        />
                      </div>
                      <b>{money(row.revenue)}</b>
                    </div>
                  ))}
                </div>
              ) : (
                <Empty text="Chưa có đơn hoàn tất trong thời gian này." />
              )}
            </section>
            <section className="panel">
              <div className="panel-heading">
                <h3>Trạng thái đơn</h3>
                <Link to="/orders">
                  <ArrowUpRight size={17} />
                </Link>
              </div>
              {d.order_statuses.length ? (
                d.order_statuses.map((s) => (
                  <div key={s.status} className="status-row">
                    <Badge>{s.status}</Badge>
                    <strong>{s.count}</strong>
                  </div>
                ))
              ) : (
                <Empty text="Chưa có đơn trong thời gian này." />
              )}
            </section>
          </div>
          <div className="dashboard-grid">
            <section className="panel">
              <div className="panel-heading">
                <h3>Thiết bị bán chạy</h3>
                <Link to="/variants">Catalog →</Link>
              </div>
              {d.bestsellers.length ? (
                <table>
                  <thead>
                    <tr>
                      <th>Thiết bị</th>
                      <th>SL bán</th>
                      <th>Doanh thu</th>
                    </tr>
                  </thead>
                  <tbody>
                    {d.bestsellers.map((r) => (
                      <tr key={r.variant_id}>
                        <td>
                          {r.name}
                          <small className="cell-secondary">{r.sku}</small>
                        </td>
                        <td>{r.quantity}</td>
                        <td>{money(r.revenue)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              ) : (
                <Empty text="Dữ liệu bán hàng sẽ xuất hiện sau khi hoàn tất đơn." />
              )}
            </section>
            <section className="stock-overview">
              <span className="eyebrow">SỨC KHỎE TỒN KHO</span>
              <h2>
                Kho hàng,
                <br />
                trong tầm nhìn.
              </h2>
              <div>
                <span>Thực tế</span>
                <strong>{d.stock.on_hand}</strong>
              </div>
              <div>
                <span>Đang giữ chỗ</span>
                <strong>{d.stock.reserved}</strong>
              </div>
              <div>
                <span>Đang vận chuyển từ nguồn</span>
                <strong>{d.stock.in_transit}</strong>
              </div>
              <div>
                <span>Số dư cảnh báo thấp</span>
                <strong>{d.stock.low_count}</strong>
              </div>
              <Link to="/inventory" className="button light">
                Xem tồn kho <ArrowUpRight size={16} />
              </Link>
            </section>
          </div>
          {report && (
            <div className="dashboard-grid">
              <section className="panel">
                <h3>Doanh thu theo chi nhánh & kênh</h3>
                {d.by_store?.length ? (
                  <table>
                    <thead>
                      <tr>
                        <th>Chi nhánh</th>
                        <th>Đơn</th>
                        <th>Doanh thu gộp</th>
                      </tr>
                    </thead>
                    <tbody>
                      {d.by_store.map((r) => (
                        <tr key={r.warehouse__store_id}>
                          <td>{r.warehouse__store__name}</td>
                          <td>{r.orders}</td>
                          <td>{money(r.revenue)}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                ) : (
                  <Empty />
                )}
                {d.by_channel?.map((r) => (
                  <p className="subtle" key={r.channel}>
                    {r.channel} · {r.orders} đơn · {money(r.revenue)}
                  </p>
                ))}
              </section>
              <section className="panel">
                <h3>Doanh thu theo tháng</h3>
                {d.monthly?.length ? (
                  <table>
                    <thead>
                      <tr>
                        <th>Tháng</th>
                        <th>Doanh thu gộp</th>
                      </tr>
                    </thead>
                    <tbody>
                      {d.monthly.map((r) => (
                        <tr key={r.month}>
                          <td>{r.month}</td>
                          <td>{money(r.revenue)}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                ) : (
                  <Empty />
                )}
                <p className="subtle">
                  {d.customers} khách có đơn trong kỳ được chọn.
                </p>
              </section>
            </div>
          )}
          <p className="fine">
            Doanh thu gộp: {money(d.sales_gross)} · Hoàn tiền:{" "}
            {money(d.refunds)} · Không tính lợi nhuận khi chưa có giá vốn.
          </p>
        </>
      ) : d && canStock ? (
        <>
          <div className="metric-grid">
            {[
              ["Tồn thực tế", d.on_hand],
              ["Giữ chỗ", d.reserved],
              ["Khả dụng", d.available],
              ["Cảnh báo thấp", d.low_count],
            ].map(([label, value]) => (
              <div className="metric" key={label}>
                <small>{label}</small>
                <strong>{value}</strong>
              </div>
            ))}
          </div>
          <Link className="button primary" to="/inventory">
            Mở tồn kho →
          </Link>
        </>
      ) : d ? (
        <section className="panel">
          <h3>Đơn hàng gần đây</h3>
          {d.results?.length ? (
            <table>
              <tbody>
                {d.results.map((o) => (
                  <tr key={o.id}>
                    <td>
                      <Link to={"/orders/" + o.id}>{o.code}</Link>
                    </td>
                    <td>{o.recipient_name}</td>
                    <td>
                      <Badge>{o.status}</Badge>
                    </td>
                    <td>{money(o.grand_total)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          ) : (
            <Empty />
          )}
          <Link className="button primary" to="/pos">
            Tạo đơn tại quầy →
          </Link>
        </section>
      ) : null}
    </>
  );
}
