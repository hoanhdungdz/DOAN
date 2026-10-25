import React, { act } from "react";
import { createRoot } from "react-dom/client";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, afterEach, expect, test, vi } from "vitest";
import CustomerLayout from "../fe/src/layouts/CustomerLayout";
import { api } from "./api";

vi.mock("./session", () => ({
  useSession: () => ({ user: { id: 7 }, signOut: vi.fn() }),
}));
vi.mock("../fe/src/features/cart/CartContext", () => ({
  useCart: () => ({ count: 2 }),
}));
vi.mock("./api", async (original) => ({ ...(await original()), api: vi.fn() }));

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

test.each([true, false])(
  "storefront mounts the RAG chat and uses the backend enabled flag (%s)",
  async (enabled) => {
    api.mockResolvedValue({ gemini: enabled });
    await act(async () =>
      root.render(
        <MemoryRouter>
          <CustomerLayout />
        </MemoryRouter>,
      ),
    );
    expect(container.querySelectorAll(".chat-toggle")).toHaveLength(1);
    expect(
      container.querySelector('[aria-label="Giỏ hàng 2 sản phẩm"]'),
    ).not.toBeNull();
    await act(async () =>
      container.querySelector('[aria-label="Mở tư vấn AI"]').click(),
    );
    expect(api).toHaveBeenCalledWith("features/");
    expect(
      container.querySelector('[aria-label="Trợ lý TechRetail"]'),
    ).not.toBeNull();
    expect(
      container.querySelector('[aria-label="Câu hỏi tư vấn"]').disabled,
    ).toBe(!enabled);
    expect(container.textContent).not.toContain("AI chưa được bật");
    if (enabled) {
      expect(container.textContent).toContain(
        "Tư vấn từ sản phẩm & chính sách cửa hàng",
      );
      expect(container.textContent).not.toContain("Trợ lý chưa được bật.");
    } else {
      expect(container.textContent).toContain("Trợ lý chưa được bật.");
    }
  },
);
