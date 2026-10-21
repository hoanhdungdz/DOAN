const base = import.meta.env.VITE_API_BASE || "/api/v1";
let csrf = "";
let csrfRequest = null;
export async function api(path, options = {}) {
  const method = (options.method || "GET").toUpperCase();
  const writes = !["GET", "HEAD", "OPTIONS", "TRACE"].includes(method);
  // Tabs of the same portal share cookies. A login in another such tab can
  // rotate CSRF without updating this module, so refresh before each mutation.
  if (writes) await initCsrf();
  const multipart =
    typeof FormData !== "undefined" && options.body instanceof FormData;
  const body = multipart
    ? options.body
    : options.body === undefined
      ? undefined
      : JSON.stringify(options.body);
  async function send() {
    const headers = new Headers(options.headers);
    if (multipart) headers.delete("Content-Type");
    else if (!headers.has("Content-Type"))
      headers.set("Content-Type", "application/json");
    if (writes) headers.set("X-CSRFToken", csrf);
    const response = await fetch(`${base}/${path.replace(/^\//, "")}`, {
      ...options,
      method,
      credentials: "include",
      headers,
      body,
    });
    const data = await response
      .json()
      .catch(() => ({ message: "Không thể đọc phản hồi máy chủ." }));
    return { response, data };
  }
  let { response, data } = await send();
  // This specific rejection happens before the view runs. Preserve the same
  // payload/idempotency key, and never retry permission/business/network errors.
  if (writes && response.status === 403 && data?.code === "CSRF_FAILED") {
    csrf = "";
    await initCsrf();
    ({ response, data } = await send());
  }
  if (!response.ok) {
    const error = new Error(data?.message || "Kết nối thất bại.");
    error.fields = data?.fields;
    error.code = data?.code;
    error.status = response.status;
    throw error;
  }
  if (data?.csrfToken) csrf = data.csrfToken;
  return data;
}
export async function initCsrf() {
  // Share an in-flight refresh so concurrent initial requests do not race to
  // create different CSRF cookies in the same tab.
  if (!csrfRequest) {
    csrfRequest = api("auth/csrf/", { cache: "no-store" })
      .then((data) => {
        if (typeof data?.csrfToken !== "string" || !data.csrfToken) {
          throw new Error(
            "Không thể khởi tạo phiên bảo mật. Vui lòng tải lại trang.",
          );
        }
        csrf = data.csrfToken;
        return csrf;
      })
      .finally(() => {
        csrfRequest = null;
      });
  }
  return csrfRequest;
}
export async function all(path) {
  let results = [];
  let page = 1;
  while (page <= 100) {
    const d = await api(
      `${path}${path.includes("?") ? "&" : "?"}page_size=100&page=${page}`,
    );
    results.push(...(d.results || []));
    if (!d.next) break;
    page++;
  }
  return results;
}
export const money = (value) =>
  new Intl.NumberFormat("vi-VN", {
    style: "currency",
    currency: "VND",
    maximumFractionDigits: 0,
  }).format(value || 0);
export const dateTime = (value) =>
  value
    ? new Intl.DateTimeFormat("vi-VN", {
        dateStyle: "short",
        timeStyle: "short",
        timeZone: "Asia/Ho_Chi_Minh",
      }).format(new Date(value))
    : "—";
export function errorText(error) {
  const fields =
    error.fields && typeof error.fields === "object"
      ? Object.entries(error.fields)
          .map(
            ([k, v]) =>
              `${k}: ${Array.isArray(v) ? v.join(", ") : JSON.stringify(v)}`,
          )
          .join(" · ")
      : "";
  return [error.message, fields].filter(Boolean).join(" ");
}
export { operationKey } from "./idempotency.js";
