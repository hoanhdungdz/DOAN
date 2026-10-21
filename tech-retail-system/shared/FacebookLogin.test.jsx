import React, { act } from "react";
import { createRoot } from "react-dom/client";
import { MemoryRouter, Routes, Route, useLocation } from "react-router-dom";
import { afterEach, beforeEach, expect, test, vi } from "vitest";
import FacebookSignInButton, {
  facebookErrorMessage,
} from "./FacebookSignInButton";
import AuthPage from "./AuthPage";
import GoogleCompletePage from "../fe/src/pages/GoogleCompletePage";
import { api } from "./api";

const state = vi.hoisted(() => ({ session: {}, merge: vi.fn() }));
vi.mock("./session", () => ({ useSession: () => state.session }));
vi.mock("../fe/src/features/cart/CartContext", () => ({
  useCart: () => ({ merge: state.merge }),
}));
vi.mock("./api", async (original) => ({ ...(await original()), api: vi.fn() }));
globalThis.IS_REACT_ACT_ENVIRONMENT = true;
let root, container;
beforeEach(() => {
  container = document.createElement("div");
  document.body.append(container);
  root = createRoot(container);
  api.mockReset();
  api.mockResolvedValue({ facebook_login: true, google_login: true });
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
      {l.search}
    </p>
  );
}
function Callback({ path = "/auth/facebook/complete?next=%2Forders%2F12" }) {
  return (
    <MemoryRouter initialEntries={[path]}>
      <Routes>
        <Route
          path="/auth/facebook/complete"
          element={<GoogleCompletePage provider="facebook" />}
        />
        <Route path="*" element={<Destination />} />
      </Routes>
    </MemoryRouter>
  );
}
test("Facebook appears alongside Google for customers only", async () => {
  for (const mode of ["login", "register"]) {
    await act(async () =>
      root.render(
        <MemoryRouter>
          <AuthPage mode={mode} />
        </MemoryRouter>,
      ),
    );
    expect(container.textContent).toContain("Đăng nhập bằng Facebook");
    expect(container.textContent).toContain("Đăng nhập bằng Google");
  }
  await act(async () =>
    root.render(
      <MemoryRouter>
        <AuthPage internal />
      </MemoryRouter>,
    ),
  );
  expect(container.textContent).not.toContain("Đăng nhập bằng Facebook");
});
test("disabled provider hides button and unknown errors are harmless", async () => {
  api.mockResolvedValue({ facebook_login: false });
  await act(async () => root.render(<FacebookSignInButton />));
  expect(container.querySelector("button")).toBeNull();
  for (const key of ["__proto__", "constructor", null, "unknown"])
    expect(facebookErrorMessage(key)).toBe("");
  expect(facebookErrorMessage("email_required")).toContain("liên kết Facebook");
});
test("button preserves destination and recovers from a failed request", async () => {
  await act(async () => root.render(<FacebookSignInButton next="/checkout" />));
  api.mockRejectedValueOnce(new Error("Mất kết nối"));
  await act(async () => container.querySelector("button").click());
  expect(api).toHaveBeenLastCalledWith("auth/facebook/start/", {
    method: "POST",
    body: { next: "/checkout", link_account: false },
  });
  expect(container.textContent).toContain("Mất kết nối");
  expect(container.querySelector("button").disabled).toBe(false);
});
test("explicit linking rejects an unexpected authorization host", async () => {
  await act(async () => root.render(<FacebookSignInButton linkAccount />));
  api.mockResolvedValueOnce({ authorization_url: "https://attacker.invalid/" });
  await act(async () => container.querySelector("button").click());
  expect(api).toHaveBeenLastCalledWith("auth/facebook/start/", {
    method: "POST",
    body: { next: "", link_account: true },
  });
  expect(container.textContent).toContain(
    "Địa chỉ đăng nhập Facebook không hợp lệ",
  );
});
test("callback requires server session and returns to the requested order after cart merge", async () => {
  await act(async () => root.render(<Callback />));
  expect(state.merge).not.toHaveBeenCalled();
  expect(container.textContent).toContain("Phiên đăng nhập không còn hiệu lực");
  state.session = { ...state.session, user: { id: 1 } };
  await act(async () => root.render(<Callback />));
  expect(state.merge).toHaveBeenCalledTimes(1);
  expect(container.textContent).toContain("destination:/orders/12");
});
test("Facebook linking returns to profile without merging guest cart", async () => {
  state.session.user = { id: 1 };
  await act(async () =>
    root.render(<Callback path="/auth/facebook/complete?linked=1" />),
  );
  expect(state.merge).not.toHaveBeenCalled();
  expect(container.textContent).toContain(
    "destination:/profile?facebook_linked=1",
  );
});
