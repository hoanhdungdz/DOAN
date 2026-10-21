import React, { act } from "react";
import { createRoot } from "react-dom/client";
import { MemoryRouter } from "react-router-dom";
import { afterEach, beforeEach, expect, test, vi } from "vitest";
import StockReceiptDialog from "../admin/src/features/resources/StockReceiptDialog";
import { api } from "./api";
vi.mock("./api", async (importOriginal) => ({
  ...(await importOriginal()),
  api: vi.fn(),
}));
globalThis.IS_REACT_ACT_ENVIRONMENT = true;
let root, container, received, closed;
beforeEach(() => {
  container = document.createElement("div");
  document.body.append(container);
  root = createRoot(container);
  received = vi.fn();
  closed = vi.fn();
  api.mockReset();
  api.mockImplementation(async (path) => {
    if (path.startsWith("warehouses/"))
      return {
        count: 1,
        results: [{ id: 4, store_name: "Cầu Giấy", name: "Kho mặc định" }],
      };
    if (path === "stock-documents/") return { id: 77, status: "DRAFT" };
    if (path === "stock-documents/77/post/")
      return { id: 77, status: "POSTED" };
    throw new Error("Unexpected API: " + path);
  });
});
afterEach(async () => {
  await act(async () => root.unmount());
  container.remove();
});
async function render() {
  await act(async () =>
    root.render(
      <MemoryRouter>
        <StockReceiptDialog
          variants={[{ id: 330, sku: "SKU-DIE-0052" }]}
          warehouse={4}
          productName="iPhone"
          onReceived={received}
          onClose={closed}
        />
      </MemoryRouter>,
    ),
  );
}
async function fill(label, value) {
  const input = [...container.querySelectorAll("label")].find((l) =>
    l.textContent.includes(label),
  ).control;
  await act(async () => {
    Object.getOwnPropertyDescriptor(
      HTMLInputElement.prototype,
      "value",
    ).set.call(input, value);
    input.dispatchEvent(new Event("input", { bubbles: true }));
  });
}
async function submit() {
  await act(async () =>
    container
      .querySelector("form")
      .dispatchEvent(new Event("submit", { bubbles: true, cancelable: true })),
  );
}
test("receiving extra stock creates an IN document, then posts that exact document", async () => {
  await render();
  await fill("Số lượng nhập thêm", "5");
  await fill("Lý do nhập hàng", "Nhập bổ sung");
  await submit();
  expect(api).toHaveBeenCalledWith("stock-documents/", {
    method: "POST",
    body: {
      warehouse: 4,
      kind: "IN",
      reason: "Nhập bổ sung",
      items: [{ variant: 330, quantity: 5 }],
    },
  });
  expect(api).toHaveBeenCalledWith("stock-documents/77/post/", {
    method: "POST",
    body: {},
  });
  expect(received).toHaveBeenCalledWith({ id: 77, status: "POSTED" });
});
test("a lost posting response retries the same document instead of creating another receipt", async () => {
  const original = api.getMockImplementation();
  let posts = 0;
  api.mockImplementation(async (path, options) => {
    if (path === "stock-documents/77/post/" && posts++ === 0)
      throw new Error("Mất phản hồi ghi sổ");
    return original(path, options);
  });
  await render();
  await fill("Lý do nhập hàng", "Nhập bổ sung");
  await submit();
  expect(received).not.toHaveBeenCalled();
  expect(container.textContent).toContain("Thử ghi sổ phiếu #77");
  expect(container.querySelector("fieldset").disabled).toBe(true);
  await submit();
  expect(
    api.mock.calls.filter(([path]) => path === "stock-documents/"),
  ).toHaveLength(1);
  expect(
    api.mock.calls.filter(([path]) => path === "stock-documents/77/post/"),
  ).toHaveLength(2);
  expect(received).toHaveBeenCalledTimes(1);
});
test("invalid quantity or missing reason never creates a stock document", async () => {
  await render();
  await submit();
  expect(container.textContent).toContain("nhập lý do nhập hàng");
  await fill("Lý do nhập hàng", "Nhập bổ sung");
  await fill("Số lượng nhập thêm", "1.5");
  await submit();
  expect(
    api.mock.calls.filter(([path]) => path === "stock-documents/"),
  ).toHaveLength(0);
});
