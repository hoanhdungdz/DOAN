import React, { useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { ArrowUpRight, ShieldCheck } from "lucide-react";
import { useSession } from "./session";
import { api, errorText } from "./api";
import { Field, ErrorBox } from "./ui";
export default function AuthPage({
  mode = "login",
  onAuthenticated,
  internal = false,
}) {
  const { authenticate } = useSession(),
    navigate = useNavigate(),
    [params] = useSearchParams();
  const [form, setForm] = useState({
      email: "",
      password: "",
      full_name: "",
      token: params.get("token") || "",
    }),
    [error, setError] = useState(""),
    [message, setMessage] = useState(""),
    [busy, setBusy] = useState(false);
  const titles = {
    login: "Chào mừng trở lại.",
    register: "Bắt đầu cùng công nghệ.",
    "forgot-password": "Tìm lại tài khoản.",
    "reset-password": "Đặt mật khẩu mới.",
  };
  async function submit(e) {
    e.preventDefault();
    setBusy(true);
    setError("");
    try {
      if (["login", "register"].includes(mode)) {
        await authenticate(mode, form);
        const warnings = onAuthenticated ? await onAuthenticated() : [];
        navigate(internal ? "/dashboard" : warnings?.length ? "/cart" : "/", {
          state: warnings?.length ? { notice: warnings.join(" ") } : undefined,
        });
      } else {
        const d = await api(`auth/${mode}/`, { method: "POST", body: form });
        setMessage(d.message);
      }
    } catch (e) {
      setError(errorText(e));
    } finally {
      setBusy(false);
    }
  }
  const input = (key, type = "text") => (
    <input
      type={type}
      required
      autoComplete={
        key === "password"
          ? mode === "login"
            ? "current-password"
            : "new-password"
          : key === "email"
            ? "email"
            : "name"
      }
      minLength={key === "password" && mode !== "login" ? 8 : undefined}
      value={form[key]}
      onChange={(e) => setForm({ ...form, [key]: e.target.value })}
    />
  );
  return (
    <main className="auth-shell">
      <section className="auth-story">
        <Link to="/" className="wordmark">
          tech<span>retail</span>
          <i>®</i>
        </Link>
        <div>
          <span className="eyebrow">
            {internal ? "KHÔNG GIAN VẬN HÀNH" : "KẾT NỐI NHỮNG KHẢ NĂNG MỚI"}
          </span>
          <h1>
            Công nghệ tốt.
            <br />
            Trải nghiệm
            <br />
            <em>trọn vẹn.</em>
          </h1>
          <p>
            {internal
              ? "Quản lý sản phẩm, đơn hàng và chi nhánh trong một không gian."
              : "Khám phá thiết bị phù hợp và theo dõi hành trình đơn hàng của bạn."}
          </p>
        </div>
        <small>
          <ShieldCheck size={16} /> Đăng nhập được bảo vệ bằng phiên máy chủ.
        </small>
      </section>
      <section className="auth-form">
        <div>
          <span className="eyebrow">TECH RETAIL / TÀI KHOẢN</span>
          <h2>{titles[mode]}</h2>
          <p className="subtle">
            {internal
              ? "Dành cho tài khoản nhân viên được quản trị viên cấp."
              : "Một tài khoản cho những trải nghiệm của bạn."}
          </p>
          <ErrorBox error={error} />
          {message ? (
            <div className="notice">
              {message}
              <Link to="/login">Quay lại đăng nhập →</Link>
            </div>
          ) : (
            <form onSubmit={submit}>
              {mode === "register" && (
                <Field label="Họ và tên">{input("full_name")}</Field>
              )}
              {mode !== "reset-password" && (
                <Field label="Email">{input("email", "email")}</Field>
              )}
              {mode === "reset-password" && (
                <Field label="Token từ email">{input("token")}</Field>
              )}
              {mode !== "forgot-password" && (
                <Field
                  label={
                    mode === "reset-password" ? "Mật khẩu mới" : "Mật khẩu"
                  }
                >
                  {input("password", "password")}
                </Field>
              )}
              {mode === "login" && (
                <Link className="small-link" to="/forgot-password">
                  Quên mật khẩu?
                </Link>
              )}
              <button className="button primary" disabled={busy}>
                {busy
                  ? "Đang xử lý…"
                  : mode === "login"
                    ? "Đăng nhập"
                    : mode === "register"
                      ? "Tạo tài khoản"
                      : "Tiếp tục"}
                <ArrowUpRight size={18} />
              </button>
            </form>
          )}
          {mode === "login" && !internal && (
            <p className="subtle">
              Chưa có tài khoản? <Link to="/register">Đăng ký</Link>
            </p>
          )}
          <p className="fine">Đăng nhập Google và Facebook chưa được bật.</p>
        </div>
      </section>
    </main>
  );
}
