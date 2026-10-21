import React, { useEffect, useState } from "react";
import { api, errorText } from "./api";
import { ErrorBox } from "./ui";

export const googleErrors = {
  cancelled: "Bạn đã hủy đăng nhập Google. Bạn có thể thử lại.",
  invalid_state:
    "Phiên đăng nhập Google đã hết hạn hoặc không khớp. Vui lòng thử lại từ trang đăng nhập.",
  verification_failed:
    "Không thể xác minh tài khoản Google. Vui lòng thử lại và kiểm tra kết nối mạng.",
  email_exists:
    "Email này đã có tài khoản. Hãy đăng nhập bằng mật khẩu, vào Hồ sơ cá nhân và chọn Liên kết tài khoản Google để giữ nguyên đơn hàng.",
  account_unavailable:
    "Tài khoản không khả dụng. Vui lòng thử lại hoặc liên hệ quản trị viên.",
  identity_in_use: "Tài khoản Google này đã liên kết với một tài khoản khác.",
  already_linked:
    "Tài khoản của bạn đã liên kết với một tài khoản Google khác.",
  not_configured: "Đăng nhập Google chưa được cấu hình.",
};

export function googleErrorMessage(code) {
  return Object.hasOwn(googleErrors, code) ? googleErrors[code] : "";
}

export default function GoogleSignInButton({ next = "", linkAccount = false }) {
  const [enabled, setEnabled] = useState(false),
    [busy, setBusy] = useState(false),
    [error, setError] = useState("");
  useEffect(() => {
    let live = true;
    api("features/")
      .then((features) => {
        if (live) setEnabled(features.google_login === true);
      })
      .catch(() => {});
    return () => {
      live = false;
    };
  }, []);
  if (!enabled) return null;
  return (
    <div className="google-sign-in">
      <ErrorBox error={error} />
      <button
        type="button"
        className="button google-button"
        disabled={busy}
        onClick={async () => {
          setBusy(true);
          setError("");
          try {
            const result = await api("auth/google/start/", {
              method: "POST",
              body: { next, link_account: linkAccount },
            });
            const url = new URL(result.authorization_url);
            if (
              url.origin !== "https://accounts.google.com" ||
              url.pathname !== "/o/oauth2/v2/auth"
            )
              throw new Error("Địa chỉ đăng nhập Google không hợp lệ.");
            window.location.assign(url.href);
          } catch (e) {
            setError(errorText(e));
            setBusy(false);
          }
        }}
      >
        <svg aria-hidden="true" width="20" height="20" viewBox="0 0 48 48">
          <path
            fill="#EA4335"
            d="M24 9.5c3.54 0 6.71 1.22 9.21 3.6l6.85-6.85C35.9 2.38 30.47 0 24 0 14.62 0 6.51 5.38 2.56 13.22l7.98 6.19C12.43 13.72 17.74 9.5 24 9.5Z"
          />
          <path
            fill="#4285F4"
            d="M46.98 24.55c0-1.57-.15-3.09-.38-4.55H24v9.02h12.94c-.58 2.96-2.26 5.48-4.78 7.18l7.73 6C44.4 38.03 46.98 31.87 46.98 24.55Z"
          />
          <path
            fill="#FBBC05"
            d="M10.53 28.59A14.41 14.41 0 0 1 9.77 24c0-1.59.27-3.13.76-4.59l-7.98-6.19A23.87 23.87 0 0 0 0 24c0 3.87.93 7.52 2.56 10.78l7.97-6.19Z"
          />
          <path
            fill="#34A853"
            d="M24 48c6.48 0 11.93-2.13 15.9-5.8l-7.73-6c-2.15 1.45-4.92 2.3-8.17 2.3-6.26 0-11.57-4.22-13.47-9.91l-7.98 6.19C6.51 42.62 14.62 48 24 48Z"
          />
        </svg>
        {busy
          ? "Đang chuyển đến Google…"
          : linkAccount
            ? "Liên kết tài khoản Google"
            : "Đăng nhập bằng Google"}
      </button>
    </div>
  );
}
