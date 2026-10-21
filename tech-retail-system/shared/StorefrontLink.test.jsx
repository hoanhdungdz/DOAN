import React, { act } from "react";
import { createRoot } from "react-dom/client";
import { afterEach, beforeEach, expect, test, vi } from "vitest";
import StorefrontLink from "../admin/src/components/StorefrontLink";
import { api } from "./api";

vi.mock("./api", () => ({ api: vi.fn(), errorText: (e) => e.message }));
globalThis.IS_REACT_ACT_ENVIRONMENT = true;
let root, container;
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
test("Open store uses the backend URL and never transfers credentials or logs out", async () => {
  api.mockResolvedValue({ customer_frontend_url: "http://localhost:6173" });
  await act(async () => root.render(<StorefrontLink />));
  const link = container.querySelector("a");
  expect(link.href).toBe("http://localhost:6173/");
  expect(link.target).toBe("_blank");
  expect(link.rel).toContain("noopener");
  expect(link.rel).toContain("noreferrer");
  expect(api.mock.calls).toEqual([["features/"]]);
});
test.each([
  "javascript:alert(1)",
  "https://user:password@shop.invalid",
  "https://shop.invalid/?token=secret",
  "https://shop.invalid/#session",
  "",
])(
  "unsafe or credential-bearing storefront URL is not opened: %s",
  async (url) => {
    api.mockResolvedValue({ customer_frontend_url: url });
    await act(async () => root.render(<StorefrontLink />));
    expect(container.querySelector("a")).toBeNull();
    expect(container.querySelector("button").disabled).toBe(true);
  },
);
test("configuration failure does not fall back to a hard-coded host", async () => {
  api.mockRejectedValue(new Error("Mất kết nối"));
  await act(async () => root.render(<StorefrontLink />));
  expect(container.querySelector("a")).toBeNull();
  expect(container.querySelector("button").disabled).toBe(true);
});
