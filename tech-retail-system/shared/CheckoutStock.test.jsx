import React, { act } from "react";
import { createRoot } from "react-dom/client";
import { MemoryRouter } from "react-router-dom";
import { afterEach, beforeEach, expect, test, vi } from "vitest";
import CartCheckout from "../fe/src/pages/CartCheckout";
import RequireAccount from "../fe/src/components/RequireAccount";
import { checkoutWarehouses } from "./checkoutStock";
import { api } from "./api";

const state = vi.hoisted(() => ({
  user: null,
  items: [],
  stock: [],
  replace: vi.fn(),
  clear: vi.fn(),
}));
vi.mock("./session", () => ({
  useSession: () => ({ user: state.user }),
}));
vi.mock("../fe/src/features/cart/CartContext", () => ({
  useCart: () => ({
    items: state.items,
    replace: state.replace,
    clear: state.clear,
    loading: false,
    error: "",
  }),
}));
vi.mock("./api", async (importOriginal) => ({
  ...(await importOriginal()),
  api: vi.fn(),
}));
globalThis.IS_REACT_ACT_ENVIRONMENT = true;
const warehouses = [
  { id: 4, store_name: "Cầu Giấy", name: "Kho A" },
  { id: 5, store_name: "Hoàng Diệu", name: "Kho B" },
];
let root, container;
beforeEach(() => {
  container = document.createElement("div");
  document.body.append(container);
  root = createRoot(container);
  state.user = { id: 1 };
  state.items = [{ variant: 330, quantity: 1 }];
  state.stock = [
    { warehouse: 4, available: 3 },
    { warehouse: 5, available: 0 },
  ];
  state.replace.mockReset();
  state.clear.mockReset();
  api.mockReset();
  api.mockImplementation(async (path, options) => {
    if (path === "auth/profile/")
      return {
        name: "Nguyễn An",
        phone: "0901234567",
        address: "12 Đường A, Hà Nội",
      };
    if (path === "checkout/promotions/") {
      const selected = options.body.coupon_code;
      const subtotal = String(16390000 * state.items[0].quantity);
      return {
        coupons: [
          {
            code: "TECH100K",
            eligible: true,
            benefit: "Giảm 100.000đ",
            condition: "Đơn từ 5.000.000đ",
            ends_at: "2026-12-31T00:00:00Z",
            per_user_limit: 1,
          },
        ],
        applied_coupon: selected === "TECH100K" ? { code: selected } : null,
        coupon_error:
          selected && selected !== "TECH100K" ? "Mã không hợp lệ" : "",
        subtotal,
        discount_total: selected === "TECH100K" ? "100000" : "0",
        grand_total: String(
          Number(subtotal) - (selected === "TECH100K" ? 100000 : 0),
        ),
      };
    }
    if (path.startsWith("warehouses/"))
      return { count: 2, results: warehouses };
    if (path.startsWith("variants/"))
      return {
        id: 330,
        sku: "SKU-DIE-0052",
        product_name: "iPhone",
        price: "16390000",
        stock: state.stock,
      };
    if (path === "carts/availability/")
      return {
        items: state.items.map((row) => ({
          ...row,
          details: {
            id: 330,
            sku: "SKU-DIE-0052",
            product_name: "iPhone",
            price: "16390000",
            stock: state.stock,
          },
        })),
        warnings: [],
      };
    throw new Error("Unexpected API: " + path);
  });
});
afterEach(async () => {
  await act(async () => root.unmount());
  container.remove();
});
const render = (checkout = true) =>
  act(async () =>
    root.render(
      <MemoryRouter>
        {checkout ? (
          <RequireAccount>
            <CartCheckout checkout />
          </RequireAccount>
        ) : (
          <CartCheckout />
        )}
      </MemoryRouter>,
    ),
  );

const recipientInputs = () =>
  container.querySelectorAll('#checkout-form input:not([type="number"])');
const inputValue = async (input, value) =>
  act(async () => {
    Object.getOwnPropertyDescriptor(
      HTMLInputElement.prototype,
      "value",
    ).set.call(input, value);
    input.dispatchEvent(new Event("input", { bubbles: true }));
  });

test("checkout fills the saved profile and submits an editable recipient without changing the profile", async () => {
  await render();
  const [name, phone, address] = recipientInputs();
  expect([name.value, phone.value, address.value]).toEqual([
    "Nguyễn An",
    "0901234567",
    "12 Đường A, Hà Nội",
  ]);
  await inputValue(name, "Người nhận khác");
  await inputValue(address, "Địa chỉ nhận khác");
  api.mockImplementationOnce(async () => ({
    id: 9,
    code: "TEST",
    grand_total: "16390000",
    payment_status: "UNPAID",
    payment_method: "COD",
  }));
  await act(async () =>
    container
      .querySelector("#checkout-form")
      .dispatchEvent(new Event("submit", { bubbles: true, cancelable: true })),
  );
  expect(
    api.mock.calls.find(([path]) => path === "orders/")[1].body,
  ).toMatchObject({
    recipient_name: "Người nhận khác",
    phone: "0901234567",
    address: "Địa chỉ nhận khác",
  });
  expect(api.mock.calls.filter(([path]) => path === "auth/profile/")).toEqual([
    ["auth/profile/"],
  ]);
});

test("a delayed profile fills only untouched fields, including preserving an intentionally cleared name", async () => {
  const original = api.getMockImplementation();
  let resolveProfile;
  api.mockImplementation((path, options) =>
    path === "auth/profile/"
      ? new Promise((resolve) => {
          resolveProfile = resolve;
        })
      : original(path, options),
  );
  await render();
  const [name, phone] = recipientInputs();
  await inputValue(name, "Tên tự nhập");
  await inputValue(name, "");
  await inputValue(phone, "0987654321");
  await act(async () =>
    resolveProfile({
      name: "Tên trong hồ sơ",
      phone: "0901234567",
      address: "Địa chỉ trong hồ sơ",
    }),
  );
  expect([...recipientInputs()].map((input) => input.value)).toEqual([
    "",
    "0987654321",
    "Địa chỉ trong hồ sơ",
  ]);
});

test("tab focus and same-account session refresh preserve recipient edits without refetching the profile", async () => {
  await render();
  await inputValue(recipientInputs()[2], "Địa chỉ đặt hộ");
  state.user = { id: 1, full_name: "Updated session" };
  await render();
  await act(async () => window.dispatchEvent(new Event("focus")));
  expect(recipientInputs()[2].value).toBe("Địa chỉ đặt hộ");
  expect(
    api.mock.calls.filter(([path]) => path === "auth/profile/"),
  ).toHaveLength(1);
});

test("switching accounts discards the previous recipient and ignores the previous account's pending profile", async () => {
  const original = api.getMockImplementation();
  const pending = [];
  api.mockImplementation((path, options) =>
    path === "auth/profile/"
      ? new Promise((resolve) => {
          pending.push(resolve);
        })
      : original(path, options),
  );
  await render();
  await inputValue(recipientInputs()[0], "Người nhận cũ");
  state.user = { id: 2 };
  await render();
  await act(async () =>
    pending[0]({
      name: "Hồ sơ cũ",
      phone: "0901234567",
      address: "Địa chỉ cũ",
    }),
  );
  expect([...recipientInputs()].map((input) => input.value)).toEqual([
    "",
    "",
    "",
  ]);
  await act(async () =>
    pending[1]({
      name: "Khách mới",
      phone: "0987654321",
      address: "Địa chỉ mới",
    }),
  );
  expect([...recipientInputs()].map((input) => input.value)).toEqual([
    "Khách mới",
    "0987654321",
    "Địa chỉ mới",
  ]);
});

test("profile failure still allows manual checkout, and the cart page never requests a profile", async () => {
  const original = api.getMockImplementation();
  api.mockImplementation((path, options) =>
    path === "auth/profile/"
      ? Promise.reject(new Error("Network unavailable"))
      : original(path, options),
  );
  await render(false);
  expect(api.mock.calls.some(([path]) => path === "auth/profile/")).toBe(false);
  await render();
  expect(container.textContent).toContain("Chưa tải được hồ sơ");
  const [name, phone, address] = recipientInputs();
  await inputValue(name, "Khách tự nhập");
  await inputValue(phone, "0901234567");
  await inputValue(address, "Địa chỉ tự nhập");
  expect(container.querySelector('button[form="checkout-form"]').disabled).toBe(
    false,
  );
  expect([...recipientInputs()].map((input) => input.value)).toEqual([
    "Khách tự nhập",
    "0901234567",
    "Địa chỉ tự nhập",
  ]);
});
test("checkout selects the branch with stock and disables the empty branch from the screenshot", async () => {
  await render();
  const select = [...container.querySelectorAll("select")].find((s) =>
    s.textContent.includes("Cầu Giấy"),
  );
  expect(select.value).toBe("4");
  expect(select.querySelector('option[value="5"]').disabled).toBe(true);
  expect(select.querySelector('option[value="5"]').textContent).toContain(
    "Hết hàng",
  );
  expect(container.textContent).toContain("Còn 3 tại Cầu Giấy");
  expect(container.querySelector('button[form="checkout-form"]').disabled).toBe(
    false,
  );
});

test("checkout applies the server quote and submits only code and agreed total with the order", async () => {
  await render();
  const use = container.querySelector('button[aria-label="Dùng mã TECH100K"]');
  await act(async () => use.click());
  expect(container.textContent).toContain("Đã áp dụng TECH100K");
  expect(container.querySelector(".summary-discount").textContent).toContain(
    "100.000",
  );
  expect(container.querySelector(".summary-total").textContent).toContain(
    "16.290.000",
  );
  api.mockImplementationOnce(async () => ({
    id: 9,
    code: "TEST",
    grand_total: "16290000",
    payment_status: "UNPAID",
    payment_method: "VNPAY_SANDBOX",
  }));
  await act(async () =>
    container
      .querySelector("#checkout-form")
      .dispatchEvent(new Event("submit", { bubbles: true, cancelable: true })),
  );
  const orderCall = api.mock.calls.find(([path]) => path === "orders/");
  expect(orderCall[1].body.coupon_code).toBe("TECH100K");
  expect(orderCall[1].body.quoted_total).toBe("16290000");
  expect(orderCall[1].body.discount_total).toBeUndefined();
  expect(container.textContent).toContain("Chưa thanh toán");
  expect(container.textContent).not.toMatch(/UNPAID|sandbox/);
  expect(container.querySelector('a[href="/orders/9"]').textContent).toBe(
    "Thanh toán qua VNPay",
  );
});

test("invalid code blocks checkout until the code is removed", async () => {
  await render();
  const input = container.querySelector("#checkout-coupon-code");
  await act(async () => {
    Object.getOwnPropertyDescriptor(
      HTMLInputElement.prototype,
      "value",
    ).set.call(input, "WRONG");
    input.dispatchEvent(new Event("input", { bubbles: true }));
  });
  await act(async () =>
    [...container.querySelectorAll("button")]
      .find((b) => b.textContent === "Áp dụng")
      .click(),
  );
  expect(container.textContent).toContain("Mã không hợp lệ");
  expect(container.querySelector('button[form="checkout-form"]').disabled).toBe(
    true,
  );
  await act(async () =>
    container.querySelector('button[aria-label="Bỏ mã giảm giá"]').click(),
  );
  expect(container.querySelector('button[form="checkout-form"]').disabled).toBe(
    false,
  );
});

test("a stale coupon response cannot price a changed basket", async () => {
  await render();
  let resolve;
  const implementation = api.getMockImplementation();
  api.mockImplementation((path, options) =>
    path === "checkout/promotions/" && options.body.coupon_code
      ? new Promise((r) => {
          resolve = r;
        })
      : implementation(path, options),
  );
  await act(async () =>
    container.querySelector('button[aria-label="Dùng mã TECH100K"]').click(),
  );
  const staleResolve = resolve;
  expect(container.querySelector('button[form="checkout-form"]').disabled).toBe(
    true,
  );
  // The user can switch cart state while this request is still in flight.
  state.items = [{ variant: 330, quantity: 2 }];
  await render();
  const currentResolve = resolve;
  await act(async () =>
    staleResolve({
      coupons: [],
      applied_coupon: { code: "TECH100K" },
      grand_total: "1",
      subtotal: "1",
      discount_total: "0",
    }),
  );
  expect(container.querySelector('button[form="checkout-form"]').disabled).toBe(
    true,
  );
  expect(container.textContent).not.toContain("Đã áp dụng TECH100K");
  await act(async () =>
    currentResolve({
      coupons: [],
      applied_coupon: { code: "TECH100K" },
      grand_total: "32680000",
      subtotal: "32780000",
      discount_total: "100000",
    }),
  );
  expect(container.querySelector(".summary-total").textContent).toContain(
    "32.680.000",
  );
  expect(container.querySelector('button[form="checkout-form"]').disabled).toBe(
    false,
  );
});
test("one warehouse must have all lines; stock cannot be pooled across branches", () => {
  const rows = [
    {
      variant: 1,
      quantity: 2,
      details: { stock: [{ warehouse: 4, available: 2 }] },
    },
    {
      variant: 2,
      quantity: 1,
      details: { stock: [{ warehouse: 5, available: 1 }] },
    },
  ];
  expect(checkoutWarehouses(warehouses, rows).some((w) => w.sufficient)).toBe(
    false,
  );
});
test("excess quantity or an unavailable product cannot pass checkout", async () => {
  state.items[0].quantity = 4;
  await render();
  expect(container.querySelector('button[form="checkout-form"]').disabled).toBe(
    true,
  );
  expect(container.textContent).toContain(
    "Chưa có chi nhánh đủ tất cả sản phẩm",
  );
  expect(
    checkoutWarehouses(warehouses, [
      { variant: 1, quantity: 1, details: null },
    ]).every((w) => !w.sufficient),
  ).toBe(true);
});
test("stock lost after selection is refreshed and blocks submission with an explicit alternative", async () => {
  await render();
  state.stock = [
    { warehouse: 4, available: 0 },
    { warehouse: 5, available: 2 },
  ];
  await act(async () => window.dispatchEvent(new Event("focus")));
  expect(container.querySelector('button[form="checkout-form"]').disabled).toBe(
    true,
  );
  expect(container.textContent).toContain("Còn 0 tại Cầu Giấy");
  const branches = [...container.querySelectorAll("select")].find((select) =>
    select.textContent.includes("Hoàng Diệu"),
  );
  await act(async () => {
    branches.value = "5";
    branches.dispatchEvent(new Event("change", { bubbles: true }));
  });
  expect(container.querySelector('button[form="checkout-form"]').disabled).toBe(
    false,
  );
  expect(container.textContent).toContain("Còn 2 tại Hoàng Diệu");
});
test("a server stock conflict reloads stock without clearing the cart or retrying checkout", async () => {
  await render();
  const original = api.getMockImplementation();
  api.mockImplementation(async (path, options) => {
    if (path === "orders/") {
      state.stock = [
        { warehouse: 4, available: 0 },
        { warehouse: 5, available: 0 },
      ];
      throw Object.assign(new Error("Kho vừa hết hàng"), {
        code: "INSUFFICIENT_STOCK",
      });
    }
    return original(path, options);
  });
  await act(async () =>
    container
      .querySelector("form#checkout-form")
      .dispatchEvent(new Event("submit", { bubbles: true, cancelable: true })),
  );
  expect(container.textContent).toContain("Kho vừa hết hàng");
  expect(container.querySelector('button[form="checkout-form"]').disabled).toBe(
    true,
  );
  expect(api.mock.calls.filter(([path]) => path === "orders/")).toHaveLength(1);
  expect(state.clear).not.toHaveBeenCalled();
});
