import React, { useEffect, useState } from "react";
import { api, errorText } from "./api";
import { ErrorBox } from "./ui";

const messages = {
  cancelled: "Bạn đã hủy đăng nhập Facebook. Bạn có thể thử lại.",
  invalid_state:
    "Phiên đăng nhập Facebook đã hết hạn hoặc không khớp. Vui lòng thử lại từ trang đăng nhập.",
  verification_failed:
    "Không thể xác minh tài khoản Facebook. Vui lòng thử lại.",
  email_exists:
    "Email này đã có tài khoản. Hãy đăng nhập bằng mật khẩu hoặc Google, vào Hồ sơ cá nhân và chọn Liên kết tài khoản Facebook để giữ nguyên đơn hàng.",
  email_required:
    "Facebook chưa cung cấp email. Hãy đăng nhập hoặc đăng ký bằng email, sau đó liên kết Facebook trong Hồ sơ cá nhân.",
  account_unavailable:
    "Tài khoản không khả dụng. Vui lòng thử lại hoặc liên hệ quản trị viên.",
  identity_in_use: "Tài khoản Facebook này đã liên kết với một tài khoản khác.",
  already_linked:
    "Tài khoản của bạn đã liên kết với một tài khoản Facebook khác.",
  not_configured: "Đăng nhập Facebook chưa được cấu hình.",
};
export function facebookErrorMessage(code) {
  return Object.hasOwn(messages, code) ? messages[code] : "";
}

export default function FacebookSignInButton({
  next = "",
  linkAccount = false,
}) {
  const [enabled, setEnabled] = useState(false),
    [busy, setBusy] = useState(false),
    [error, setError] = useState("");
  useEffect(() => {
    let live = true;
    api("features/")
      .then((f) => {
        if (live) setEnabled(f.facebook_login === true);
      })
      .catch(() => {});
    return () => {
      live = false;
    };
  }, []);
  if (!enabled) return null;
  return (
    <div className="facebook-sign-in">
      <ErrorBox error={error} />
      <button
        type="button"
        className="button facebook-button"
        disabled={busy}
        onClick={async () => {
          setBusy(true);
          setError("");
          try {
            const result = await api("auth/facebook/start/", {
              method: "POST",
              body: { next, link_account: linkAccount },
            });
            const url = new URL(result.authorization_url);
            if (
              url.origin !== "https://www.facebook.com" ||
              !/^\/v\d+\.\d+\/dialog\/oauth$/.test(url.pathname)
            )
              throw new Error("Địa chỉ đăng nhập Facebook không hợp lệ.");
            window.location.assign(url.href);
          } catch (e) {
            setError(errorText(e));
            setBusy(false);
          }
        }}
      >
        <svg aria-hidden="true" width="22" height="22" viewBox="0 0 24 24">
          <path
            fill="currentColor"
            d="M13.5 22v-9h3l.5-3.5h-3.5V7.2c0-1 .3-1.7 1.8-1.7H17V2.4c-.3 0-1.3-.1-2.5-.1-2.5 0-4.2 1.5-4.2 4.3v2.9H7.5V13h2.8v9z"
          />
        </svg>
        {busy
          ? "Đang chuyển đến Facebook…"
          : linkAccount
            ? "Liên kết tài khoản Facebook"
            : "Đăng nhập bằng Facebook"}
      </button>
    </div>
  );
}
