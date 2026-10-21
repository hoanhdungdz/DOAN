import React, { act } from "react";
import { createRoot } from "react-dom/client";
import { afterEach, beforeEach, expect, test, vi } from "vitest";
import CheckoutPromotions from "../fe/src/components/CheckoutPromotions";

globalThis.IS_REACT_ACT_ENVIRONMENT = true;
let root, container;
beforeEach(() => {
  container = document.createElement("div");
  document.body.append(container);
  root = createRoot(container);
});
afterEach(async () => {
  await act(async () => root.unmount());
  container.remove();
});
const data = {
  coupons: [
    {
      code: "TECH100K",
      eligible: true,
      benefit: "Giảm 100.000đ",
      condition: "Đơn từ 5 triệu",
      ends_at: "2026-12-31T00:00:00Z",
      per_user_limit: 1,
    },
    {
      code: "PHUKIEN50K",
      eligible: false,
      benefit: "Giảm 50.000đ",
      reason: "Giỏ chưa có phụ kiện",
      ends_at: "2026-12-31T00:00:00Z",
      per_user_limit: 1,
    },
  ],
};
test("unavailable coupon shows the server reason and cannot be chosen", async () => {
  const onSelect = vi.fn();
  await act(async () =>
    root.render(
      <CheckoutPromotions quote={data} code="" onSelect={onSelect} />,
    ),
  );
  const unavailable = container.querySelector(
    'button[aria-label="Dùng mã PHUKIEN50K"]',
  );
  expect(unavailable.disabled).toBe(true);
  expect(container.textContent).toContain("Giỏ chưa có phụ kiện");
  await act(async () =>
    container.querySelector('button[aria-label="Dùng mã TECH100K"]').click(),
  );
  expect(onSelect).toHaveBeenCalledWith("TECH100K");
});
test("selected coupon can be removed and manual entry is normalized", async () => {
  const onSelect = vi.fn();
  await act(async () =>
    root.render(
      <CheckoutPromotions
        quote={{ ...data, applied_coupon: { code: "TECH100K" } }}
        code="TECH100K"
        onSelect={onSelect}
      />,
    ),
  );
  expect(
    container.querySelector('[aria-pressed="true"]').textContent,
  ).toContain("Đã chọn");
  await act(async () =>
    container.querySelector('button[aria-label="Bỏ mã giảm giá"]').click(),
  );
  expect(onSelect).toHaveBeenCalledWith("");
  const input = container.querySelector("input");
  await act(async () => {
    Object.getOwnPropertyDescriptor(
      HTMLInputElement.prototype,
      "value",
    ).set.call(input, " chao5 ");
    input.dispatchEvent(new Event("input", { bubbles: true }));
  });
  await act(async () =>
    [...container.querySelectorAll("button")]
      .find((b) => b.textContent === "Áp dụng")
      .click(),
  );
  expect(onSelect).toHaveBeenLastCalledWith("CHAO5");
});
