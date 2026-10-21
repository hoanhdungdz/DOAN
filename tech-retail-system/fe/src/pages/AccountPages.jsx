import React, { useEffect, useState } from "react";
import { promptReason } from "../../../shared/dialogs";
import { Link, useParams, useSearchParams } from "react-router-dom";
import GoogleSignInButton, {
  googleErrorMessage,
} from "../../../shared/GoogleSignInButton";
import FacebookSignInButton, {
  facebookErrorMessage,
} from "../../../shared/FacebookSignInButton";
import { api, money, dateTime, errorText } from "../../../shared/api";
import { useSession } from "../../../shared/session";
import {
  Loading,
  ErrorBox,
  Empty,
  Field,
  Badge,
  Pager,
} from "../../../shared/ui";
import useRemote from "../hooks/useRemote";
import VnpayPaymentPanel from "../../../shared/VnpayPaymentPanel";
export function OrderPage() {
  const { id } = useParams(),
    [page, setPage] = useState(1),
    [revision, setRevision] = useState(0),
    [actionError, setActionError] = useState(""),
    [busy, setBusy] = useState(false),
    remote = useRemote(
      id ? `my-orders/${id}/` : `my-orders/?page=${page}`,
      revision,
    );
  const o = id ? remote.data : null;
  return (
    <main className="content-width account-page">
      <span className="eyebrow">TÀI KHOẢN / ĐƠN HÀNG</span>
      {id && (
        <Link to="/orders" className="back-link">
          ← Đơn hàng của tôi
        </Link>
      )}
      <h1>{o ? o.code : "Đơn hàng của tôi"}</h1>
      <ErrorBox error={remote.error || actionError} />
      {remote.loading ? (
        <Loading />
      ) : o ? (
        <>
          <div className="panel">
            <div className="order-meta">
              <Badge>{o.status}</Badge>
              <Badge>{o.payment_status}</Badge>
              <span>{dateTime(o.created_at)}</span>
              <span>{o.store_name}</span>
            </div>
            <table>
              <thead>
                <tr>
                  <th>Sản phẩm</th>
                  <th>Số lượng</th>
                  <th>Đơn giá</th>
                  <th>Thành tiền</th>
                </tr>
              </thead>
              <tbody>
                {o.items.map((i) => (
                  <tr key={i.id}>
                    <td>
                      {i.name}
                      <small className="fine"> · {i.sku}</small>
                    </td>
                    <td>{i.quantity}</td>
                    <td>{money(i.unit_price)}</td>
                    <td>{money(i.line_total)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
            {o.coupon_code && (
              <p className="subtle">
                Tiền hàng: {money(o.subtotal)} · Mã {o.coupon_code}: −
                {money(o.discount_total)}
              </p>
            )}
            <p className="print-total">Tổng cộng: {money(o.grand_total)}</p>
            <p className="subtle">
              {o.recipient_name} · {o.phone}
              <br />
              {o.address}
            </p>
            {o.status === "PENDING" && (
              <button
                disabled={busy}
                onClick={async () => {
                  const reason = await promptReason("Lý do hủy đơn:");
                  if (!reason) return;
                  setBusy(true);
                  try {
                    await api(`my-orders/${o.id}/cancel/`, {
                      method: "POST",
                      body: { reason },
                    });
                    setRevision((r) => r + 1);
                  } catch (e) {
                    setActionError(errorText(e));
                  } finally {
                    setBusy(false);
                  }
                }}
              >
                Hủy đơn đang chờ
              </button>
            )}
          </div>
          {o.payment_method === "VNPAY_SANDBOX" && (
            <VnpayPaymentPanel
              key={o.id}
              order={o}
              onChange={() => setRevision((r) => r + 1)}
            />
          )}
          <section className="panel order-timeline">
            <h3>Tiến trình</h3>
            {o.history.map((h) => (
              <p key={h.id}>
                <Badge>{h.status}</Badge> {dateTime(h.created_at)}{" "}
                <span className="subtle">{h.reason}</span>
              </p>
            ))}
          </section>
        </>
      ) : remote.data?.results?.length ? (
        <div className="panel">
          <table>
            <thead>
              <tr>
                <th>Mã đơn</th>
                <th>Ngày đặt</th>
                <th>Trạng thái</th>
                <th>Tổng tiền</th>
                <th />
              </tr>
            </thead>
            <tbody>
              {remote.data.results.map((o) => (
                <tr key={o.id}>
                  <td>{o.code}</td>
                  <td>{dateTime(o.created_at)}</td>
                  <td>
                    <Badge>{o.status}</Badge>
                  </td>
                  <td>{money(o.grand_total)}</td>
                  <td>
                    <Link to={"/orders/" + o.id}>Xem chi tiết →</Link>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          <Pager page={page} setPage={setPage} count={remote.data.count} />
        </div>
      ) : (
        !remote.error && <Empty text="Bạn chưa có đơn hàng nào." />
      )}
    </main>
  );
}
export function ProfilePage() {
  const [params] = useSearchParams();
  const { user } = useSession(),
    [form, setForm] = useState(null),
    [error, setError] = useState(""),
    [message, setMessage] = useState(""),
    [busy, setBusy] = useState(false),
    [passwords, setPasswords] = useState({
      current_password: "",
      password: "",
    });
  useEffect(() => {
    if (user)
      api("auth/profile/")
        .then(setForm)
        .catch((e) => setError(errorText(e)));
  }, [user?.id]);
  if (!user)
    return (
      <main className="success panel">
        <h2>Hồ sơ của bạn</h2>
        <Link className="button primary" to="/login">
          Đăng nhập
        </Link>
      </main>
    );
  return (
    <main className="content-width account-page">
      <span className="eyebrow">TÀI KHOẢN</span>
      <h1>Xin chào, {user.full_name || user.email}.</h1>
      <ErrorBox error={error} />
      <ErrorBox error={googleErrorMessage(params.get("google_error"))} />
      <ErrorBox error={facebookErrorMessage(params.get("facebook_error"))} />
      {params.get("facebook_linked") === "1" && user.facebook_linked && (
        <div className="notice">
          Đã liên kết tài khoản Facebook. Bạn có thể dùng Facebook để đăng nhập.
        </div>
      )}
      {params.get("google_linked") === "1" && user.google_linked && (
        <p className="notice">
          Đã liên kết tài khoản Google. Bạn có thể dùng Google để đăng nhập vào
          tài khoản này.
        </p>
      )}
      {message && <p className="notice">{message}</p>}
      <div className="split">
        <section className="panel">
          <h3>Hồ sơ cá nhân</h3>
          {form ? (
            <form
              onSubmit={async (e) => {
                e.preventDefault();
                setBusy(true);
                try {
                  await api("auth/profile/", { method: "PATCH", body: form });
                  setMessage("Đã lưu hồ sơ.");
                  setError("");
                } catch (e) {
                  setError(errorText(e));
                } finally {
                  setBusy(false);
                }
              }}
            >
              {[
                ["name", "Họ và tên"],
                ["phone", "Điện thoại"],
                ["email", "Email liên hệ"],
                ["address", "Địa chỉ"],
              ].map(([k, label]) => (
                <Field key={k} label={label}>
                  <input
                    required={k === "name"}
                    type={k === "email" ? "email" : "text"}
                    value={form[k]}
                    onChange={(e) => setForm({ ...form, [k]: e.target.value })}
                  />
                </Field>
              ))}
              <button className="button primary" disabled={busy}>
                Lưu thông tin
              </button>
            </form>
          ) : (
            <Loading />
          )}
        </section>
        <section className="panel">
          <h3>Đổi mật khẩu</h3>
          <p className="subtle">
            Sau khi đổi mật khẩu, các phiên cũ sẽ không còn hiệu lực.
          </p>
          <form
            onSubmit={async (e) => {
              e.preventDefault();
              setBusy(true);
              try {
                await api("auth/change-password/", {
                  method: "POST",
                  body: passwords,
                });
                window.location.assign("/login");
              } catch (e) {
                setError(errorText(e));
              } finally {
                setBusy(false);
              }
            }}
          >
            <Field label="Mật khẩu hiện tại">
              <input
                required
                type="password"
                autoComplete="current-password"
                value={passwords.current_password}
                onChange={(e) =>
                  setPasswords({
                    ...passwords,
                    current_password: e.target.value,
                  })
                }
              />
            </Field>
            <Field label="Mật khẩu mới">
              <input
                required
                minLength={8}
                type="password"
                autoComplete="new-password"
                value={passwords.password}
                onChange={(e) =>
                  setPasswords({ ...passwords, password: e.target.value })
                }
              />
            </Field>
            <button className="button" disabled={busy}>
              Đổi mật khẩu
            </button>
          </form>
        </section>
      </div>
      <section className="panel">
        <h3>Đăng nhập Google</h3>
        {user.google_linked ? (
          <p className="subtle">Tài khoản đã liên kết với Google.</p>
        ) : (
          <>
            <p className="subtle">
              Liên kết Google với tài khoản hiện tại để giữ nguyên hồ sơ và lịch
              sử đơn hàng.
            </p>
            <GoogleSignInButton linkAccount />
          </>
        )}
      </section>
      <section className="panel">
        <h3>Đăng nhập Facebook</h3>
        {user.facebook_linked ? (
          <p className="subtle">Tài khoản đã liên kết với Facebook.</p>
        ) : (
          <>
            <p className="subtle">
              Liên kết Facebook với tài khoản hiện tại để giữ nguyên hồ sơ và
              lịch sử đơn hàng.
            </p>
            <FacebookSignInButton linkAccount />
          </>
        )}
      </section>
      <p>
        <Link to="/orders">Xem lịch sử đơn hàng →</Link>
      </p>
    </main>
  );
}
