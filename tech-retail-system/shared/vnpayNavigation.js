export function safeVnpayUrl(value) {
  try {
    const url = new URL(value);
    return url.origin === "https://sandbox.vnpayment.vn" &&
      url.pathname === "/paymentv2/vpcpay.html" &&
      !url.username &&
      !url.password &&
      !url.hash
      ? url.href
      : "";
  } catch {
    return "";
  }
}

export function redirectToVnpay(value) {
  const url = safeVnpayUrl(value);
  if (!url) throw new Error("Địa chỉ thanh toán VNPay không hợp lệ.");
  window.location.assign(url);
}
