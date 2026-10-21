import React, { act } from "react";
import { createRoot } from "react-dom/client";
import { afterEach, beforeEach, expect, test, vi } from "vitest";
import { SessionProvider, useSession } from "./session";
import { api } from "./api";

vi.mock("./api", () => ({ api: vi.fn() }));
globalThis.IS_REACT_ACT_ENVIRONMENT = true;
let root, container, current;
function Probe() {
  current = useSession();
  return (
    <p>
      {current.loading ? "loading" : current.user?.id || "anonymous"}{" "}
      {current.error}
    </p>
  );
}
beforeEach(() => {
  container = document.createElement("div");
  document.body.append(container);
  root = createRoot(container);
  api.mockReset();
});
afterEach(async () => {
  await act(async () => root.unmount());
  container.remove();
});
test("focus and visibility revalidate the cookie shared across ports, single flight", async () => {
  api.mockResolvedValue({ user: { id: 1 } });
  await act(async () =>
    root.render(
      <SessionProvider>
        <Probe />
      </SessionProvider>,
    ),
  );
  expect(current.user.id).toBe(1);
  let resolve;
  api.mockImplementation(
    () =>
      new Promise((r) => {
        resolve = r;
      }),
  );
  await act(async () => {
    window.dispatchEvent(new Event("focus"));
    document.dispatchEvent(new Event("visibilitychange"));
  });
  expect(api).toHaveBeenCalledTimes(2);
  expect(current.loading).toBe(false);
  await act(async () => resolve({ user: { id: 2 } }));
  expect(current.user.id).toBe(2);
});
test("an old refresh cannot restore the previous account after login or logout", async () => {
  let resolveOld;
  api.mockImplementation((path) =>
    path === "auth/me/"
      ? new Promise((r) => {
          resolveOld = r;
        })
      : Promise.resolve({ user: { id: 2 } }),
  );
  await act(async () =>
    root.render(
      <SessionProvider>
        <Probe />
      </SessionProvider>,
    ),
  );
  await act(async () => current.authenticate("login", {}));
  await act(async () => resolveOld({ user: { id: 1 } }));
  expect(current.user.id).toBe(2);
  await act(async () => window.dispatchEvent(new Event("focus")));
  await act(async () => current.signOut());
  await act(async () => resolveOld({ user: { id: 2 } }));
  expect(current.user).toBeNull();
});
test("failed revalidation removes stale private session data", async () => {
  api.mockResolvedValue({ user: { id: 1 } });
  await act(async () =>
    root.render(
      <SessionProvider>
        <Probe />
      </SessionProvider>,
    ),
  );
  api.mockRejectedValue(new Error("Mất kết nối"));
  await act(async () => window.dispatchEvent(new Event("focus")));
  expect(current.user).toBeNull();
  expect(current.error).toBe("Mất kết nối");
});
