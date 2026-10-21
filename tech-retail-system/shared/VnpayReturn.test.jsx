import React, { act } from "react";
import { createRoot } from "react-dom/client";
import { MemoryRouter } from "react-router-dom";
import { afterEach, beforeEach, expect, test, vi } from "vitest";
import VnpayReturnPage from "../fe/src/pages/VnpayReturnPage";
import { api } from "./api";

const session = vi.hoisted(() => ({
  user: { id: 1 },
  loading: false,
  refresh: vi.fn(),
}));
vi.mock("./session", () => ({ useSession: () => session }));
vi.mock("./api", async (original) => ({ ...(await original()), api: vi.fn() }));
globalThis.IS_REACT_ACT_ENVIRONMENT = true;
let root, container, attempt, order;
const reference = "b".repeat(32),
  statusPath = `payments/vnpay/attempts/${reference}/`,
  checkPath = statusPath + "check/";
beforeEach(() => {
  vi.useFakeTimers();
  session.user = { id: 1 };
  session.loading = false;
  session.refresh.mockClear();
  container = document.createElement("div");
  document.body.append(container);
  root = createRoot(container);
  attempt = {
    reference,
    order: 9,
    amount: "1234000.00",
    status: "PENDING",
    order_payment_status: "UNPAID",
    expires_at: new Date(Date.now() + 900000).toISOString(),
  };
  order = {
    id: 9,
    code: "RETURN-ORDER",
    grand_total: "1234000.00",
    payment_status: "UNPAID",
    status: "PENDING",
  };
  api.mockReset();
  api.mockImplementation(async (path) =>
    path === "my-orders/9/" ? order : attempt,
  );
});
afterEach(async () => {
  await act(async () => root.unmount());
  container.remove();
  vi.restoreAllMocks();
  vi.useRealTimers();
});
const render = (query = `reference=${reference}`) =>
  act(async () =>
    root.render(
      <MemoryRouter initialEntries={[`/payments/vnpay/return?${query}`]}>
        <VnpayReturnPage />
      </MemoryRouter>,
    ),
  );
const confirmed = (extra = {}) => ({
  ...attempt,
  status: "SUCCEEDED",
  order_payment_status: "PAID",
  provider_transaction: "987654",
  ...extra,
});
const heading = () => container.querySelector("h1")?.textContent;
const queries = () => api.mock.calls.filter(([path]) => path === checkPath);

test("return page automatically queries VNPay and displays success without pressing a button", async () => {
  api.mockImplementation(async (path) =>
    path === "my-orders/9/"
      ? order
      : path === checkPath
        ? confirmed()
        : attempt,
  );
  await render();
  expect(api).toHaveBeenCalledWith(checkPath, { method: "POST", body: {} });
  expect(heading()).toBe("Thanh toán thành công");
  expect(container.textContent).toContain("987654");
  expect(container.querySelector('a[href="/orders/9"]')).not.toBeNull();
  expect(container.textContent).not.toMatch(
    /Kiểm tra kết quả thanh toán|Thanh toán ngay/,
  );
  const calls = api.mock.calls.length;
  await act(async () => vi.advanceTimersByTimeAsync(120000));
  expect(api.mock.calls).toHaveLength(calls);
});
test("already verified IPN result is shown immediately without querying the provider again", async () => {
  attempt = confirmed();
  await render();
  expect(heading()).toBe("Thanh toán thành công");
  expect(queries()).toHaveLength(0);
});
test("pending confirmation does not offer a second payment and waits for the actual server result", async () => {
  let finish;
  api.mockImplementation(async (path) =>
    path === "my-orders/9/"
      ? order
      : path === checkPath
        ? new Promise((resolve) => {
            finish = resolve;
          })
        : attempt,
  );
  await render();
  expect(heading()).toBe("Đang xác nhận thanh toán");
  expect(container.textContent).not.toContain("Thanh toán ngay");
  expect(container.textContent).not.toContain("Chưa thanh toán");
  await act(async () => vi.advanceTimersByTimeAsync(8000));
  expect(queries()).toHaveLength(1);
  await act(async () => finish(confirmed()));
  expect(heading()).toBe("Thanh toán thành công");
});
test("delayed IPN can finish polling even when QueryDR is temporarily unavailable", async () => {
  let reads = 0;
  api.mockImplementation(async (path) => {
    if (path === "my-orders/9/") return order;
    if (path === checkPath)
      throw Object.assign(new Error("VNPay đang bận"), { status: 503 });
    reads++;
    return reads > 1 ? confirmed() : attempt;
  });
  await render();
  expect(heading()).toBe("Đang xác nhận thanh toán");
  await act(async () => vi.advanceTimersByTimeAsync(4000));
  expect(heading()).toBe("Thanh toán thành công");
  expect(queries()).toHaveLength(1);
});
test("bounded automatic recovery times out honestly and never starts a new payment", async () => {
  await render();
  await act(async () => vi.advanceTimersByTimeAsync(60000));
  expect(heading()).toBe("Chưa nhận được kết quả thanh toán");
  expect(queries()).toHaveLength(4);
  expect(api.mock.calls.some(([path]) => path.endsWith("/vnpay/"))).toBe(false);
  const calls = api.mock.calls.length;
  await act(async () => vi.advanceTimersByTimeAsync(60000));
  expect(api.mock.calls).toHaveLength(calls);
  const retry = [...container.querySelectorAll("button")].find(
    (button) => button.textContent === "Thử xác nhận lại",
  );
  api.mockImplementation(async (path) =>
    path === "my-orders/9/" ? order : confirmed(),
  );
  await act(async () => retry.click());
  expect(heading()).toBe("Thanh toán thành công");
});
test("a failed verified transaction is a result page rather than another checkout", async () => {
  attempt = { ...attempt, status: "FAILED" };
  await render();
  expect(heading()).toBe("Thanh toán chưa thành công");
  expect(queries()).toHaveLength(0);
  expect(container.textContent).not.toContain("Thanh toán ngay");
});
test("expired attempts still reconcile late payments and show review instead of false success", async () => {
  attempt.expires_at = new Date(Date.now() - 10000).toISOString();
  api.mockImplementation(async (path) =>
    path === "my-orders/9/"
      ? { ...order, status: "CANCELLED" }
      : path === checkPath
        ? {
            ...attempt,
            status: "REVIEW",
            order_payment_status: "REFUND_PENDING",
            review_reason: "Cần kiểm tra hoàn tiền",
          }
        : attempt,
  );
  await render();
  expect(queries()).toHaveLength(1);
  expect(heading()).toBe("Giao dịch cần kiểm tra");
  expect(container.textContent).toContain("Cần kiểm tra hoàn tiền");
});
test("confirmed result shows shop and provider discounts without subtracting twice", async () => {
  order = { ...order, discount_total: "100000", coupon_code: "TECH100K" };
  attempt = confirmed({
    promotion_code: "CTT0604",
    promotion_amount: "100000",
    customer_amount: "1134000",
  });
  await render();
  expect(container.textContent).toContain("TECH100K");
  expect(container.textContent).toContain("CTT0604");
  expect(container.querySelector(".vnpay-result-total").textContent).toContain(
    "1.134.000",
  );
});
test("invalid or anonymous return pages never query a payment", async () => {
  await render("reference=invalid&vnp_ResponseCode=00");
  expect(api).not.toHaveBeenCalled();
  session.user = null;
  await render();
  expect(api).not.toHaveBeenCalled();
});
test("owner denial stops all queries and clears the previous account result", async () => {
  let finish;
  api.mockImplementation(async (path) =>
    path === "my-orders/9/"
      ? order
      : path === checkPath
        ? new Promise((resolve) => {
            finish = resolve;
          })
        : attempt,
  );
  await render();
  expect(container.textContent).toContain("RETURN-ORDER");
  session.user = { id: 2 };
  api.mockRejectedValue(Object.assign(new Error("Not found"), { status: 404 }));
  await render();
  expect(container.textContent).not.toContain("RETURN-ORDER");
  expect(container.textContent).toContain("đăng nhập tài khoản đã đặt đơn");
  await act(async () => finish(confirmed()));
  expect(container.textContent).not.toContain("Thanh toán thành công");
  const calls = api.mock.calls.length;
  await act(async () => vi.advanceTimersByTimeAsync(120000));
  expect(api.mock.calls).toHaveLength(calls);
});
test("a hidden return page waits until visible before querying the provider", async () => {
  const visibility = vi
    .spyOn(document, "visibilityState", "get")
    .mockReturnValue("hidden");
  await render();
  expect(queries()).toHaveLength(0);
  api.mockImplementation(async (path) =>
    path === "my-orders/9/"
      ? order
      : path === checkPath
        ? confirmed()
        : attempt,
  );
  visibility.mockReturnValue("visible");
  await act(async () => document.dispatchEvent(new Event("visibilitychange")));
  expect(queries()).toHaveLength(1);
  expect(heading()).toBe("Thanh toán thành công");
});
test("provider throttling does not cause a query loop or claim payment failed", async () => {
  api.mockImplementation(async (path) => {
    if (path === "my-orders/9/") return order;
    if (path === checkPath)
      throw Object.assign(new Error("Thử lại sau"), { status: 429 });
    return attempt;
  });
  await render();
  await act(async () => vi.advanceTimersByTimeAsync(60000));
  expect(queries()).toHaveLength(1);
  expect(heading()).toBe("Chưa nhận được kết quả thanh toán");
});
