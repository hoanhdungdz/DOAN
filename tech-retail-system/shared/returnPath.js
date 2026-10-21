export function customerReturnPath(value) {
  if (typeof value !== "string" || /[\\\u0000-\u0020]/.test(value)) return "";
  // Only known customer destinations can be used after authentication.
  return /^\/(?:orders(?:\/[1-9]\d*)?|cart|checkout|profile)(?:\?[^#]*)?$/.test(
    value,
  )
    ? value
    : "";
}
