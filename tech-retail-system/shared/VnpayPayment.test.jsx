import React, { act } from "react";
import { createRoot } from "react-dom/client";
import { MemoryRouter } from "react-router-dom";
import { afterEach, beforeEach, expect, test, vi } from "vitest";
import VnpayPaymentPanel, { safeVnpayUrl } from "./VnpayPaymentPanel";
import VnpayReturnPage from "../fe/src/pages/VnpayReturnPage";
import { api } from "./api";
import { redirectToVnpay } from "./vnpayNavigation";

const session = vi.hoisted(() => ({
  user: { id: 1 },
  loading: false,
  refresh: vi.fn(),
}));
vi.mock("./session", () => ({ useSession: () => session }));
vi.mock("./api", async (original) => ({ ...(await original()), api: vi.fn() }));
vi.mock("./vnpayNavigation", async (original) => ({
  ...(await original()),
  redirectToVnpay: vi.fn(),
}));
globalThis.IS_REACT_ACT_ENVIRONMENT = true;
const ref = "a".repeat(32),
  url = "https://sandbox.vnpayment.vn/paymentv2/vpcpay.html?vnp_TxnRef=" + ref;
let root, container, order, payment;
beforeEach(() => {
  container = document.createElement("div");
  document.body.append(container);
  root = createRoot(container);
  order = {
    id: 9,
    code: "TEST-ORDER",
    grand_total: "1234000.00",
    payment_method: "VNPAY_SANDBOX",
    payment_status: "UNPAID",
    status: "PENDING",
  };
  payment = {
    reference: ref,
    order: 9,
    amount: "1234000.00",
    status: "PENDING",
    order_payment_status: "UNPAID",
    expires_at: new Date(Date.now() + 900000).toISOString(),
    bank_mode: "",
    payment_url: url,
  };
  session.user = { id: 1 };
  session.refresh.mockClear();
  api.mockReset();
  redirectToVnpay.mockClear();
  api.mockImplementation(async (path) =>
    path === "features/"
      ? { vnpay_sandbox: true }
      : path === "my-orders/9/"
        ? order
        : payment,
  );
});
afterEach(async () => {
  await act(async () => root.unmount());
  container.remove();
});
const button = (name) =>
  [...container.querySelectorAll("button")].find((b) =>
    b.textContent.includes(name),
  );

test("unconfigured gateway disables create instead of inventing a QR", async () => {
  api.mockResolvedValue({ vnpay_sandbox: false });
  await act(async () => root.render(<VnpayPaymentPanel order={order} />));
  expect(button("Thanh toán ngay").disabled).toBe(true);
  expect(container.textContent).toContain("chưa khả dụng");
  expect(container.querySelector("a")).toBeNull();
});
test("one payment action validates with the owner endpoint and redirects without a second click", async () => {
  await act(async () => root.render(<VnpayPaymentPanel order={order} />));
  await act(async () => button("Thanh toán ngay").click());
  expect(api).toHaveBeenCalledWith("my-orders/9/vnpay/", {
    method: "POST",
    body: { bank_mode: "" },
  });
  expect(redirectToVnpay).toHaveBeenCalledExactlyOnceWith(url);
  expect(container.querySelector("a")).toBeNull();
  expect(container.textContent).not.toMatch(/sandbox|Tạo thanh toán|Mở cổng/);
  expect(container.textContent).not.toContain("Đã nhận xác nhận thanh toán");
});
test("server paid status refreshes order and hides payment link", async () => {
  payment.status = "SUCCEEDED";
  payment.order_payment_status = "PAID";
  payment.payment_url = null;
  const changed = vi.fn();
  await act(async () =>
    root.render(
      <VnpayPaymentPanel
        order={{ ...order, vnpay_payment: { reference: ref } }}
        onChange={changed}
      />,
    ),
  );
  expect(changed).toHaveBeenCalledTimes(1);
  expect(container.textContent).toContain("Đã nhận xác nhận thanh toán");
  expect(container.querySelector("a")).toBeNull();
});
test("cancellation or late payment review does not offer another payment", async () => {
  order.status = "CANCELLED";
  payment.status = "REVIEW";
  payment.review_reason = "Cần kiểm tra hoàn tiền";
  await act(async () =>
    root.render(
      <VnpayPaymentPanel order={{ ...order, vnpay_payment: payment }} />,
    ),
  );
  expect(container.textContent).toContain("Cần kiểm tra hoàn tiền");
  expect(button("Thanh toán ngay")).toBeUndefined();
});
test("network failure permits retry and external payment hosts are rejected", async () => {
  await act(async () => root.render(<VnpayPaymentPanel order={order} />));
  api.mockRejectedValueOnce(new Error("Mất kết nối"));
  await act(async () => button("Thanh toán ngay").click());
  expect(container.textContent).toContain("Mất kết nối");
  expect(button("Thanh toán ngay").disabled).toBe(false);
  for (const value of [
    "https://attacker.invalid/",
    "https://sandbox.vnpayment.vn.attacker.invalid/paymentv2/vpcpay.html",
    "http://sandbox.vnpayment.vn/paymentv2/vpcpay.html",
    "https://user@sandbox.vnpayment.vn/paymentv2/vpcpay.html",
  ])
    expect(safeVnpayUrl(value)).toBe("");
});
test("an existing payment still revalidates on the server before redirecting", async () => {
  await act(async () =>
    root.render(
      <VnpayPaymentPanel order={{ ...order, vnpay_payment: payment }} />,
    ),
  );
  const nextUrl = url + "&validated=1";
  api.mockResolvedValueOnce({ ...payment, payment_url: nextUrl });
  await act(async () => button("Thanh toán ngay").click());
  expect(api).toHaveBeenCalledWith("my-orders/9/vnpay/", {
    method: "POST",
    body: { bank_mode: "" },
  });
  expect(redirectToVnpay).toHaveBeenCalledExactlyOnceWith(nextUrl);
});
test("double clicks submit one request and unsafe returned URLs never redirect", async () => {
  await act(async () => root.render(<VnpayPaymentPanel order={order} />));
  let resolve;
  api.mockImplementationOnce(
    () =>
      new Promise((r) => {
        resolve = r;
      }),
  );
  await act(async () => {
    const pay = button("Thanh toán ngay");
    pay.click();
    pay.click();
  });
  expect(
    api.mock.calls.filter(([path]) => path === "my-orders/9/vnpay/"),
  ).toHaveLength(1);
  expect(button("Đang chuyển đến VNPay").disabled).toBe(true);
  await act(async () =>
    resolve({ ...payment, payment_url: "https://attacker.invalid/" }),
  );
  expect(redirectToVnpay).not.toHaveBeenCalled();
  expect(container.textContent).toContain(
    "Địa chỉ thanh toán VNPay không hợp lệ",
  );
  expect(button("Thanh toán ngay").disabled).toBe(false);
});
test("changing accounts before payment creation finishes prevents a stale redirect", async () => {
  await act(async () => root.render(<VnpayPaymentPanel order={order} />));
  let resolve;
  api.mockImplementationOnce(
    () =>
      new Promise((r) => {
        resolve = r;
      }),
  );
  await act(async () => button("Thanh toán ngay").click());
  session.user = { id: 2 };
  await act(async () =>
    root.render(<VnpayPaymentPanel order={{ ...order, id: 10 }} />),
  );
  await act(async () => resolve(payment));
  expect(redirectToVnpay).not.toHaveBeenCalled();
});
test("a cancelled unpaid order cannot start another payment", async () => {
  await act(async () =>
    root.render(
      <VnpayPaymentPanel order={{ ...order, status: "CANCELLED" }} />,
    ),
  );
  expect(button("Thanh toán ngay")).toBeUndefined();
  expect(container.textContent).toContain(
    "không còn ở trạng thái có thể thanh toán",
  );
});
test("return query alone cannot mark an order paid", async () => {
  await act(async () =>
    root.render(
      <MemoryRouter
        initialEntries={[
          `/payments/vnpay/return?reference=${ref}&vnp_ResponseCode=00`,
        ]}
      >
        <VnpayReturnPage />
      </MemoryRouter>,
    ),
  );
  expect(api).toHaveBeenCalledWith(`payments/vnpay/attempts/${ref}/`);
  expect(container.textContent).not.toContain("Đã nhận xác nhận thanh toán");
  expect(container.textContent).toContain("sau khi nhận xác nhận từ VNPay");
});

test("manual check queries the provider on the server and shows both offers", async () => {
  order.discount_total = "100000.00";
  order.coupon_code = "TECH100K";
  await act(async () =>
    root.render(
      <VnpayPaymentPanel order={{ ...order, vnpay_payment: payment }} />,
    ),
  );
  const confirmed = {
    ...payment,
    status: "SUCCEEDED",
    order_payment_status: "PAID",
    promotion_code: "CTT0604",
    promotion_amount: "100000.00",
    customer_amount: "1134000.00",
    payment_url: null,
  };
  api.mockImplementation(async (path) =>
    path === "features/" ? { vnpay_sandbox: true } : confirmed,
  );
  await act(async () => button("Kiểm tra kết quả").click());
  expect(api).toHaveBeenCalledWith(`payments/vnpay/attempts/${ref}/check/`, {
    method: "POST",
    body: {},
  });
  expect(container.textContent).toContain("Mã cửa hàng TECH100K");
  expect(container.textContent).toContain("Ưu đãi VNPay CTT0604");
  expect(container.textContent).toContain("1.134.000");
  expect(container.querySelector("a")).toBeNull();
});

test("owner rejection removes cached payment and stops polling", async () => {
  vi.useFakeTimers();
  try {
    api.mockImplementation(async (path) => {
      if (path === "features/") return { vnpay_sandbox: true };
      throw Object.assign(
        new Error("No VnpayAttempt matches the given query."),
        { status: 404 },
      );
    });
    await act(async () =>
      root.render(
        <VnpayPaymentPanel order={{ ...order, vnpay_payment: payment }} />,
      ),
    );
    const calls = api.mock.calls.length;
    await act(async () => vi.advanceTimersByTime(12000));
    expect(api.mock.calls.length).toBe(calls);
    expect(container.textContent).toContain("đăng nhập tài khoản đã đặt đơn");
    expect(container.textContent).not.toContain("No VnpayAttempt");
    expect(container.textContent).not.toContain("TEST-ORDER");
    expect(container.querySelector(`a[href^="https://sandbox"]`)).toBeNull();
    expect(session.refresh).toHaveBeenCalledOnce();
  } finally {
    vi.useRealTimers();
  }
});

test("return page drops previous account order immediately and ignores stale requests", async () => {
  const view = (
    <MemoryRouter initialEntries={[`/payments/vnpay/return?reference=${ref}`]}>
      <VnpayReturnPage />
    </MemoryRouter>
  );
  await act(async () => root.render(view));
  expect(container.textContent).toContain("TEST-ORDER");
  let rejectNew;
  api.mockImplementation(
    () =>
      new Promise((_, reject) => {
        rejectNew = reject;
      }),
  );
  session.user = { id: 2 };
  await act(async () =>
    root.render(
      <MemoryRouter
        initialEntries={[`/payments/vnpay/return?reference=${ref}`]}
      >
        <VnpayReturnPage />
      </MemoryRouter>,
    ),
  );
  expect(container.textContent).not.toContain("TEST-ORDER");
  expect(container.querySelector(`a[href="/orders/9"]`)).toBeNull();
  await act(async () =>
    rejectNew(
      Object.assign(new Error("No VnpayAttempt matches the given query."), {
        status: 404,
      }),
    ),
  );
  expect(container.textContent).toContain("đăng nhập tài khoản đã đặt đơn");
  expect(container.textContent).not.toContain("No VnpayAttempt");
});
