import React, { act } from "react";
import { createRoot } from "react-dom/client";
import { MemoryRouter, Routes, Route, useLocation } from "react-router-dom";
import { afterEach, beforeEach, expect, test, vi } from "vitest";
import GoogleSignInButton, { googleErrorMessage } from "./GoogleSignInButton";
import AuthPage from "./AuthPage";
import GoogleCompletePage from "../fe/src/pages/GoogleCompletePage";
import { api } from "./api";

const state = vi.hoisted(() => ({ session: {}, merge: vi.fn() }));
vi.mock("./session", () => ({ useSession: () => state.session }));
vi.mock("../fe/src/features/cart/CartContext", () => ({
  useCart: () => ({ merge: state.merge }),
}));
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
  api.mockResolvedValue({ google_login: true });
  state.merge.mockReset();
  state.merge.mockResolvedValue([]);
  state.session = {
    user: null,
    loading: false,
    error: "",
    authenticate: vi.fn(),
  };
});
afterEach(async () => {
  await act(async () => root.unmount());
  container.remove();
});
function Destination() {
  const l = useLocation();
  return (
    <p>
      destination:{l.pathname}
      {l.search}:{l.state?.notice}
    </p>
  );
}
function Callback({ path = "/auth/google/complete?next=%2Forders%2F12" }) {
  return (
    <MemoryRouter initialEntries={[path]}>
      <Routes>
        <Route path="/auth/google/complete" element={<GoogleCompletePage />} />
        <Route path="*" element={<Destination />} />
      </Routes>
    </MemoryRouter>
  );
}
test("customer login and registration show Google when configured, employee login does not", async () => {
  for (const mode of ["login", "register"]) {
    await act(async () =>
      root.render(
        <MemoryRouter>
          <AuthPage mode={mode} />
        </MemoryRouter>,
      ),
    );
    expect(container.textContent).toContain("Đăng nhập bằng Google");
  }
  await act(async () =>
    root.render(
      <MemoryRouter>
        <AuthPage internal />
      </MemoryRouter>,
    ),
  );
  expect(container.textContent).not.toContain("Đăng nhập bằng Google");
});
test("unrecognized error query parameters cannot render object properties", () => {
  for (const code of ["__proto__", "constructor", "unknown", null])
    expect(googleErrorMessage(code)).toBe("");
  expect(googleErrorMessage("email_exists")).toContain("giữ nguyên đơn hàng");
});
test("a disabled provider never offers a nonfunctional Google button", async () => {
  api.mockResolvedValue({ google_login: false });
  await act(async () => root.render(<GoogleSignInButton />));
  expect(container.querySelector("button")).toBe(null);
});
test("Google button preserves destination, posts through CSRF API and recovers from failure", async () => {
  await act(async () => root.render(<GoogleSignInButton next="/orders/12" />));
  api.mockRejectedValueOnce(new Error("Mất kết nối"));
  await act(async () => container.querySelector("button").click());
  expect(api).toHaveBeenLastCalledWith("auth/google/start/", {
    method: "POST",
    body: { next: "/orders/12", link_account: false },
  });
  expect(container.textContent).toContain("Mất kết nối");
  expect(container.querySelector("button").disabled).toBe(false);
});
test("account linking is an explicit operation and unexpected destinations are blocked", async () => {
  await act(async () => root.render(<GoogleSignInButton linkAccount />));
  api.mockResolvedValueOnce({ authorization_url: "https://attacker.invalid/" });
  await act(async () => container.querySelector("button").click());
  expect(api).toHaveBeenLastCalledWith("auth/google/start/", {
    method: "POST",
    body: { next: "", link_account: true },
  });
  expect(container.textContent).toContain(
    "Địa chỉ đăng nhập Google không hợp lệ",
  );
});
test("return page waits for a verified server session before merging cart and returning to order details", async () => {
  state.session.loading = true;
  await act(async () => root.render(<Callback />));
  expect(state.merge).not.toHaveBeenCalled();
  state.session = { ...state.session, loading: false, user: { id: 12 } };
  await act(async () => root.render(<Callback />));
  expect(state.merge).toHaveBeenCalledTimes(1);
  expect(container.textContent).toContain("destination:/orders/12");
});
test("return page cannot log in a visitor from a success URL alone", async () => {
  await act(async () => root.render(<Callback />));
  expect(state.merge).not.toHaveBeenCalled();
  expect(container.textContent).toContain("Phiên đăng nhập không còn hiệu lực");
});
test("link completion returns to profile without merging the anonymous cart", async () => {
  state.session.user = { id: 12 };
  await act(async () =>
    root.render(
      <Callback path="/auth/google/complete?linked=1&next=%2Fprofile" />,
    ),
  );
  expect(state.merge).not.toHaveBeenCalled();
  expect(container.textContent).toContain(
    "destination:/profile?google_linked=1",
  );
});
test("cart merge failure leaves the guest cart available for recovery", async () => {
  state.session.user = { id: 12 };
  state.merge.mockRejectedValueOnce(new Error("Không thể gộp giỏ hàng"));
  await act(async () => root.render(<Callback />));
  expect(container.textContent).toContain("Không thể gộp giỏ hàng");
  expect(container.querySelector('a[href="/cart"]')).not.toBe(null);
});
