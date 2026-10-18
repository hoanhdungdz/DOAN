import React, { act } from "react";
import { createRoot } from "react-dom/client";
import { beforeEach, afterEach, test, expect, vi } from "vitest";
import ProductWarranty from "../fe/src/components/ProductWarranty";
import { productWarranty, warrantyDescription } from "./warranty";

globalThis.IS_REACT_ACT_ENVIRONMENT = true;
let container, root;
const product = { name: "Máy kiểm thử", category_name: "Máy tính để bàn" };
const variant = {
  id: 1,
  sku: "TEST-1",
  condition: "Mới 100% (Chính hãng)",
  warranty_months: 12,
};
beforeEach(() => {
  container = document.createElement("div");
  document.body.append(container);
  root = createRoot(container);
  // jsdom does not implement the browser's modal-dialog methods.
  Object.defineProperties(HTMLDialogElement.prototype, {
    showModal: {
      configurable: true,
      value: vi.fn(function () {
        this.setAttribute("open", "");
      }),
    },
    close: {
      configurable: true,
      value: vi.fn(function () {
        this.removeAttribute("open");
      }),
    },
  });
});
afterEach(async () => {
  await act(async () => root.unmount());
  container.remove();
  delete HTMLDialogElement.prototype.showModal;
  delete HTMLDialogElement.prototype.close;
});

test("selected variant drives card and dialog, while category selects relevant coverage", async () => {
  await act(async () =>
    root.render(<ProductWarranty product={product} variant={variant} />),
  );
  expect(container.textContent).toContain("Bảo hành 12 tháng chính hãng.");
  await act(async () => container.querySelector("button").click());
  const dialog = document.querySelector("dialog");
  expect(dialog.open).toBe(true);
  expect(dialog.textContent).toContain("Không bao gồm màn hình");
  expect(dialog.textContent).not.toContain("Pin tích hợp");
  expect(document.body.style.overflow).toBe("hidden");
  await act(async () =>
    root.render(
      <ProductWarranty
        product={product}
        variant={{ ...variant, warranty_months: 6, condition: "Đã kích hoạt" }}
      />,
    ),
  );
  expect(container.textContent).toContain("Bảo hành 6 tháng tại Tech Retail.");
  expect(dialog.textContent).toContain("6 tháng tại Tech Retail");
  expect(dialog.textContent).not.toContain("12 tháng chính hãng");
  await act(async () => dialog.querySelector("button").click());
  expect(dialog.open).toBe(false);
  expect(document.body.style.overflow).toBe("");
});

test("Escape closes the dialog and navigation unmount restores page scrolling", async () => {
  document.body.style.overflow = "auto";
  await act(async () =>
    root.render(<ProductWarranty product={product} variant={variant} />),
  );
  await act(async () => container.querySelector("button").click());
  await act(async () =>
    document.querySelector("dialog").dispatchEvent(new Event("cancel")),
  );
  expect(document.querySelector("dialog").open).toBe(false);
  expect(document.body.style.overflow).toBe("auto");
  await act(async () => container.querySelector("button").click());
  await act(async () => root.render(null));
  expect(document.body.style.overflow).toBe("auto");
  document.body.style.overflow = "";
});

test("all stored durations remain distinct and missing/zero durations never acquire default coverage", () => {
  for (const months of [6, 12, 18, 24]) {
    const policy = productWarranty(product, {
      ...variant,
      warranty_months: months,
    });
    expect(policy.summary).toContain(`${months} tháng`);
    expect(policy.accessoryMonths).toBeLessThanOrEqual(months);
  }
  expect(
    productWarranty(product, { ...variant, warranty_months: 0 }).summary,
  ).toContain("không áp dụng");
  for (const raw of [null, undefined, "", -1, "invalid"]) {
    expect(
      productWarranty(product, { ...variant, warranty_months: raw }).months,
    ).toBe(null);
  }
});

test("conflicting warranty periods in marketing text follow the selected variant without mutating source", () => {
  const source = "Laptop cũ, bảo hành 6-12 tháng, đổi mới 30 ngày.";
  const policy = productWarranty(product, {
    ...variant,
    warranty_months: 24,
    condition: "Cũ đẹp (Like New)",
  });
  expect(warrantyDescription(source, policy)).toBe(
    "Laptop cũ, Bảo hành 24 tháng tại Tech Retail, đổi mới 30 ngày.",
  );
  expect(source).toContain("6-12 tháng");
});
