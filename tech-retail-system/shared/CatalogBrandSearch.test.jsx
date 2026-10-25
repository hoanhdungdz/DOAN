import React, { act } from "react";
import { createRoot } from "react-dom/client";
import { MemoryRouter, useLocation } from "react-router-dom";
import { test, expect, vi } from "vitest";
import CatalogPage from "../fe/src/pages/CatalogPage";
import { all } from "./api";
vi.mock("./api", async (original) => ({ ...(await original()), all: vi.fn() }));
vi.mock("../fe/src/hooks/useRemote", () => ({
  default: (path) => ({
    loading: false,
    error: "",
    data: {
      count: 0,
      results: path.startsWith("categories") ? [{ id: 1, name: "Laptop" }] : [],
    },
  }),
}));
globalThis.IS_REACT_ACT_ENVIRONMENT = true;
function CurrentQuery() {
  return <output>{useLocation().search}</output>;
}
test("brand filter searches all loaded names and writes IDs while preserving other filters", async () => {
  all.mockResolvedValue([
    ...Array.from({ length: 120 }, (_, index) => ({
      id: index + 1,
      name: `Hãng ${index + 1}`,
    })),
    { id: 501, name: "Apple" },
  ]);
  const container = document.createElement("div");
  document.body.append(container);
  const root = createRoot(container);
  try {
    await act(async () =>
      root.render(
        <MemoryRouter initialEntries={["/products?category=1&price_min=123"]}>
          <CatalogPage />
          <CurrentQuery />
        </MemoryRouter>,
      ),
    );
    const input = container.querySelector('[aria-label="Thương hiệu"]');
    await act(async () => input.focus());
    await act(async () => {
      Object.getOwnPropertyDescriptor(
        HTMLInputElement.prototype,
        "value",
      ).set.call(input, "apple");
      input.dispatchEvent(new Event("input", { bubbles: true }));
    });
    expect(all).toHaveBeenCalledWith("brands/");
    const option = container.querySelector('[role="option"]');
    expect(option.textContent).toBe("Apple");
    await act(async () => option.click());
    const query = container.querySelector("output").textContent;
    expect(query).toContain("brand=501");
    expect(query).toContain("category=1");
    expect(query).toContain("price_min=123");
    expect(input.value).toBe("Apple");
  } finally {
    await act(async () => root.unmount());
    container.remove();
  }
});
