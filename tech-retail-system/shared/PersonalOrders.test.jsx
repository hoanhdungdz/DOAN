import React, { act } from "react";
import { createRoot } from "react-dom/client";
import { MemoryRouter, Routes, Route, useLocation } from "react-router-dom";
import { afterEach, beforeEach, expect, test, vi } from "vitest";
import RequireAccount from "../fe/src/components/RequireAccount";
import { OrderPage } from "../fe/src/pages/AccountPages";
import { customerReturnPath } from "./returnPath";
import { api } from "./api";

const state = vi.hoisted(() => ({ session: {} }));
vi.mock("./session", () => ({ useSession: () => state.session }));
vi.mock("./api", async (importOriginal) => ({
  ...(await importOriginal()),
  api: vi.fn(),
}));
globalThis.IS_REACT_ACT_ENVIRONMENT = true;
let root, container;
beforeEach(() => {
  container = document.createElement("div");
  document.body.append(container);
  root = createRoot(container);
  api.mockReset();
  state.session = { user: null, loading: false, error: "", refresh: vi.fn() };
});
afterEach(async () => {
  await act(async () => root.unmount());
  container.remove();
});
function LoginMarker() {
  const l = useLocation();
  return <p>login:{new URLSearchParams(l.search).get("next")}</p>;
}
function App({ path = "/orders" }) {
  return (
    <MemoryRouter initialEntries={[path]}>
      <Routes>
        <Route path="/login" element={<LoginMarker />} />
        <Route
          path="/orders"
          element={
            <RequireAccount>
              <OrderPage />
            </RequireAccount>
          }
        />
        <Route
          path="/orders/:id"
          element={
            <RequireAccount>
              <OrderPage />
            </RequireAccount>
          }
        />
      </Routes>
    </MemoryRouter>
  );
}

test("anonymous users are sent to login with the original detail URL and no private request", async () => {
  await act(async () => root.render(<App path="/orders/12" />));
  expect(container.textContent).toContain("login:/orders/12");
  expect(api).not.toHaveBeenCalled();
});

test("session loading and errors never mount private order content", async () => {
  state.session.loading = true;
  await act(async () => root.render(<App />));
  expect(api).not.toHaveBeenCalled();
  state.session = { ...state.session, loading: false, error: "Server offline" };
  await act(async () => root.render(<App />));
  expect(container.textContent).toContain("Server offline");
  expect(api).not.toHaveBeenCalled();
});

test("authenticated history uses the strict personal API and contains no OTP controls", async () => {
  state.session.user = { id: 10 };
  api.mockResolvedValue({
    count: 1,
    results: [
      {
        id: 12,
        code: "MY-ORDER",
        status: "PENDING",
        grand_total: "100000",
        created_at: "2026-10-19T10:00:00Z",
      },
    ],
  });
  await act(async () => root.render(<App />));
  expect(api).toHaveBeenCalledWith("my-orders/?page=1");
  expect(container.textContent).toContain("MY-ORDER");
  expect(container.textContent).not.toContain("OTP");
  expect(container.querySelector('a[href="/orders/12"]')).not.toBe(null);
});

test("switching accounts clears the first account's order rows before the next response", async () => {
  state.session.user = { id: 10 };
  api.mockResolvedValueOnce({
    count: 1,
    results: [
      {
        id: 12,
        code: "FIRST-ACCOUNT-PRIVATE",
        status: "PENDING",
        grand_total: "100000",
      },
    ],
  });
  await act(async () => root.render(<App />));
  expect(container.textContent).toContain("FIRST-ACCOUNT-PRIVATE");
  let finish;
  api.mockImplementationOnce(
    () =>
      new Promise((resolve) => {
        finish = resolve;
      }),
  );
  state.session.user = { id: 20 };
  await act(async () => root.render(<App />));
  expect(container.textContent).not.toContain("FIRST-ACCOUNT-PRIVATE");
  await act(async () => finish({ count: 0, results: [] }));
  expect(container.textContent).toContain("Bạn chưa có đơn hàng nào");
});

test("only local customer destinations are accepted after login", () => {
  for (const path of [
    "/orders",
    "/orders/12",
    "/orders?page=2",
    "/checkout",
    "/cart",
  ])
    expect(customerReturnPath(path)).toBe(path);
  for (const path of [
    "https://evil.test",
    "//evil.test",
    "/\\evil.test",
    "/dashboard",
    "/login",
    "/orders/0",
    " /orders",
    null,
  ])
    expect(customerReturnPath(path)).toBe("");
});
