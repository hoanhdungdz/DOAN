import React, { useEffect, useState } from "react";
import { promptReason } from "../../../shared/dialogs";
import { Link, useParams } from "react-router-dom";
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
export function OrderPage() {
  const { id } = useParams(),
    { user, loading: sessionLoading } = useSession(),
    [page, setPage] = useState(1),
    [revision, setRevision] = useState(0),
    [actionError, setActionError] = useState(""),
    [busy, setBusy] = useState(false),
    remote = useRemote(id ? `orders/${id}/` : `orders/?page=${page}`, revision);
  if (sessionLoading) return <Loading />;
  if (!user)
    return (
      <main className="content-width success panel">
        <h2>Theo dõi đơn hàng</h2>
        <p>
          Đăng nhập để xem đơn đã đặt bằng tài khoản, hoặc xác minh OTP cho đơn
          khách vãng lai.
        </p>
        <Link className="button primary" to="/login">
          Đăng nhập
        </Link>
        <Link className="button" to="/lookup">
          Tra cứu bằng OTP
        </Link>
      </main>
    );
  const o = id ? remote.data : null;
  return (
    <main className="content-width account-page">
      <span className="eyebrow">TÀI KHOẢN / ĐƠN HÀNG</span>
      <h1>{o ? o.code : "Hành trình đơn hàng."}</h1>
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
                    await api(`orders/${o.id}/cancel/`, {
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
export function LookupPage() {
  const [form, setForm] = useState({ code: "", phone: "", otp: "" }),
    [challenge, setChallenge] = useState(""),
    [order, setOrder] = useState(null),
    [error, setError] = useState(""),
    [message, setMessage] = useState(""),
    [busy, setBusy] = useState(false);
  async function submit(e) {
    e.preventDefault();
    setBusy(true);
    setError("");
    try {
      if (!challenge) {
        const d = await api("order-lookup/request/", {
          method: "POST",
          body: form,
        });
        setChallenge(d.challenge);
        setMessage(
          d.message +
            (d.delivery_mode === "development"
              ? " Chế độ development: SMS mô phỏng nằm trong inbox local của backend."
              : ""),
        );
      } else {
        await api("order-lookup/verify/", {
          method: "POST",
          body: { challenge, otp: form.otp },
        });
        setOrder(await api("order-lookup/result/"));
      }
    } catch (e) {
      setError(errorText(e));
    } finally {
      setBusy(false);
    }
  }
  return (
    <main className="content-width lookup-page">
      <span className="eyebrow">THEO DÕI / TRA CỨU AN TOÀN</span>
      <h1>Đơn hàng đến đâu rồi?</h1>
      <p className="subtle">
        Tra cứu bằng mã đơn và số điện thoại đã dùng khi đặt hàng.
      </p>
      <ErrorBox error={error} />
      {order ? (
        <section className="panel">
          <h2>{order.code}</h2>
          <div className="order-meta">
            <Badge>{order.status}</Badge>
            <Badge>{order.payment_status}</Badge>
          </div>
          {order.items.map((i, k) => (
            <p key={k}>
              {i.name} × {i.quantity} · {money(i.unit_price)}
            </p>
          ))}
          <strong>{money(order.grand_total)}</strong>
          <button
            className="button"
            onClick={() => {
              setOrder(null);
              setChallenge("");
              setMessage("");
            }}
          >
            Tra cứu đơn khác
          </button>
        </section>
      ) : (
        <form className="panel" onSubmit={submit}>
          {!challenge ? (
            <>
              <Field label="Mã đơn">
                <input
                  required
                  maxLength={30}
                  value={form.code}
                  onChange={(e) => setForm({ ...form, code: e.target.value })}
                />
              </Field>
              <Field label="Số điện thoại">
                <input
                  required
                  type="tel"
                  value={form.phone}
                  onChange={(e) => setForm({ ...form, phone: e.target.value })}
                />
              </Field>
            </>
          ) : (
            <>
              <p className="notice">{message}</p>
              <Field label="Mã OTP 6 chữ số">
                <input
                  required
                  pattern="[0-9]{6}"
                  maxLength={6}
                  inputMode="numeric"
                  value={form.otp}
                  onChange={(e) => setForm({ ...form, otp: e.target.value })}
                />
              </Field>
              <button
                type="button"
                onClick={() => {
                  setChallenge("");
                  setMessage("");
                }}
              >
                Đổi thông tin / yêu cầu gửi lại
              </button>
            </>
          )}
          <button className="button primary" disabled={busy}>
            {busy
              ? "Đang xử lý…"
              : challenge
                ? "Xác minh và xem đơn"
                : "Yêu cầu mã xác minh"}
          </button>
        </form>
      )}
    </main>
  );
}
export function ProfilePage() {
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
      <p>
        <Link to="/orders">Xem lịch sử đơn hàng →</Link>
      </p>
    </main>
  );
}
