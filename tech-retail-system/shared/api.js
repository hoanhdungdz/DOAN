const base = import.meta.env.VITE_API_BASE || "/api/v1";
let csrf = "";
export async function api(path, options = {}) {
  const method = options.method || "GET";
  if (!["GET", "HEAD"].includes(method) && !csrf) await initCsrf();
  const response = await fetch(`${base}/${path.replace(/^\//, "")}`, {
    ...options,
    method,
    credentials: "include",
    headers: {
      "Content-Type": "application/json",
      ...(csrf ? { "X-CSRFToken": csrf } : {}),
      ...options.headers,
    },
    body: options.body === undefined ? undefined : JSON.stringify(options.body),
  });
  const data = await response
    .json()
    .catch(() => ({ message: "Không thể đọc phản hồi máy chủ." }));
  if (!response.ok) {
    const error = new Error(data.message || "Kết nối thất bại.");
    error.fields = data.fields;
    error.code = data.code;
    error.status = response.status;
    throw error;
  }
  if (data.csrfToken) csrf = data.csrfToken;
  return data;
}
export async function initCsrf() {
  const data = await api("auth/csrf/");
  csrf = data.csrfToken;
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
