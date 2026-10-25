import React, { act, useState } from "react";
import { createRoot } from "react-dom/client";
import { beforeEach, afterEach, test, expect, vi } from "vitest";
import SearchSelect from "./SearchSelect";
import StructuredData from "./StructuredData";
import { vietnamLocal, vietnamIso } from "./vietnamTime";
import ResourceForm from "../admin/src/features/resources/ResourceForm";
import { resources } from "../admin/src/features/resources/config";
import ProductRecordDetails from "../admin/src/features/resources/ProductRecordDetails";
import { api, all } from "./api";

vi.mock("./api", async (original) => ({
  ...(await original()),
  api: vi.fn(),
  all: vi.fn(),
}));
vi.mock("./session", () => ({
  useSession: () => ({ user: { is_admin: true } }),
}));
globalThis.IS_REACT_ACT_ENVIRONMENT = true;
let root, container, saved;
beforeEach(() => {
  container = document.createElement("div");
  document.body.append(container);
  root = createRoot(container);
  api.mockReset();
  api.mockResolvedValue({});
  all.mockReset();
  all.mockResolvedValue([]);
  saved = vi.fn();
});
afterEach(async () => {
  await act(async () => root.unmount());
  container.remove();
});
async function render(component) {
  await act(async () => root.render(component));
}
async function value(input, text) {
  await act(async () => {
    Object.getOwnPropertyDescriptor(
      input.tagName === "SELECT"
        ? HTMLSelectElement.prototype
        : HTMLInputElement.prototype,
      "value",
    ).set.call(input, text);
    input.dispatchEvent(
      new Event(input.tagName === "SELECT" ? "change" : "input", {
        bubbles: true,
      }),
    );
  });
}
async function submit() {
  await act(async () =>
    container
      .querySelector("form")
      .dispatchEvent(new Event("submit", { bubbles: true, cancelable: true })),
  );
}
const byLabel = (label) => container.querySelector(`[aria-label="${label}"]`);
function Lookup() {
  const [selected, setSelected] = useState("");
  return (
    <>
      <SearchSelect
        label="Kho"
        required
        options={[
          { value: 3, label: "Cầu Giấy — Kho Điều Chuyển" },
          { value: 4, label: "Thanh Xuân — Kho trung tâm" },
        ]}
        value={selected}
        onChange={setSelected}
      />
      <output>{selected}</output>
    </>
  );
}

test("lookup searches Vietnamese names without accents, selects IDs by keyboard and clears", async () => {
  await render(<Lookup />);
  const input = byLabel("Kho");
  await act(async () => input.focus());
  await value(input, "dieu chuyen");
  expect(container.textContent).toContain("Kho Điều Chuyển");
  expect(container.textContent).not.toContain("Kho trung tâm");
  for (const key of ["ArrowDown", "Enter"])
    await act(async () =>
      input.dispatchEvent(new KeyboardEvent("keydown", { key, bubbles: true })),
    );
  expect(container.querySelector("output").textContent).toBe("3");
  expect(input.value).toContain("Cầu Giấy");
  await act(async () => byLabel("Bỏ chọn kho").click());
  expect(container.querySelector("output").textContent).toBe("");
  expect(input.checkValidity()).toBe(false);
});
test("free text cannot satisfy a required selection, and absent names show a clear empty state", async () => {
  await render(<Lookup />);
  const input = byLabel("Kho");
  await act(async () => input.focus());
  await value(input, "khong co kho nay");
  expect(input.checkValidity()).toBe(false);
  expect(container.textContent).toContain("Không tìm thấy");
  await act(async () =>
    input.dispatchEvent(
      new KeyboardEvent("keydown", { key: "Escape", bubbles: true }),
    ),
  );
  expect(input.getAttribute("aria-expanded")).toBe("false");
});
test("JSON details become nested labeled lists and cannot execute HTML", async () => {
  await render(
    <StructuredData
      value={{
        name: "Laptop",
        attributes: '{"RAM":"16 GB","ports":["USB-C","HDMI"]}',
        is_active: true,
        description: "<img src=x onerror=alert(1)>",
      }}
    />,
  );
  expect(container.querySelectorAll("dl").length).toBeGreaterThan(1);
  expect(container.textContent).toContain("Thuộc tính");
  expect(container.textContent).toContain("16 GB");
  expect(container.textContent).toContain("USB-C");
  expect(container.querySelector("pre")).toBeNull();
  expect(container.querySelector("img")).toBeNull();
  expect(container.textContent).not.toContain("[object Object]");
});

test("product detail prioritizes name, price, stock and parsed specifications over source metadata", async () => {
  await render(
    <ProductRecordDetails
      product={{
        id: 4,
        name: "Laptop dễ đọc",
        category_name: "Laptop",
        brand_name: "ASUS",
        is_active: true,
        description: "Mô tả",
        variants: [
          {
            id: 7,
            sku: "SKU-7",
            name: "Mặc định",
            price: "12300000",
            condition: "Mới",
            warranty_months: 12,
            is_active: true,
            stock: [{ warehouse: 1, store_name: "Cầu Giấy", available: 3 }],
          },
        ],
        specifications: [{ id: 9, name: "Bộ nhớ", value: '{"RAM":"16 GB"}' }],
        source_id: "source-4",
      }}
    />,
  );
  expect(container.querySelector("h3").textContent).toBe("Laptop dễ đọc");
  expect(container.textContent).toContain("3 khả dụng");
  expect(container.textContent).toContain("16 GB");
  expect(container.querySelector("details").textContent).toContain("source-4");
  expect(container.querySelector("pre")).toBeNull();
});
test("malformed JSON remains readable text, empty values and zero are preserved", async () => {
  await render(
    <StructuredData
      value={{ raw_specs: '{"RAM":broken', available: 0, images: [] }}
    />,
  );
  expect(container.textContent).toContain('{"RAM":broken');
  expect(container.textContent).toContain("0");
  expect(container.textContent).toContain("Chưa có dữ liệu");
});
test("voucher conversion is Vietnam time at midnight and rejects impossible dates", () => {
  expect(vietnamLocal("2026-10-21T17:05:00Z")).toBe("2026-10-22T00:05");
  expect(vietnamIso("2026-10-22T00:05")).toBe("2026-10-21T17:05:00.000Z");
  expect(vietnamIso("2026-10-22T23:59")).toBe("2026-10-22T16:59:00.000Z");
  expect(() => vietnamIso("2026-02-30T12:00")).toThrow();
  expect(() => vietnamIso("2026-10-22T24:00")).toThrow();
});
const coupon = {
  id: 21,
  code: "TEST100",
  name: "Thử giờ",
  discount_type: "FIXED",
  value: "100000",
  min_subtotal: "0",
  max_discount: null,
  categories: [],
  first_order_only: false,
  per_user_limit: 1,
  usage_limit: 10,
  starts_at: "2026-10-21T17:05:27Z",
  ends_at: "2026-10-23T16:59:00Z",
  is_active: true,
};
test("voucher editor uses explicit 24-hour controls and preserves unchanged timestamp precision", async () => {
  await render(
    <ResourceForm
      name="coupons"
      config={resources.coupons}
      record={coupon}
      onSaved={saved}
      onClose={() => {}}
    />,
  );
  expect(byLabel("Ngày bắt đầu").value).toBe("2026-10-22");
  expect(byLabel("Giờ bắt đầu").value).toBe("00");
  expect(byLabel("Phút bắt đầu").value).toBe("05");
  expect(container.querySelector('[type="datetime-local"]')).toBeNull();
  await value(byLabel("Giờ kết thúc"), "20");
  await submit();
  const body = api.mock.calls[0][1].body;
  expect(body.starts_at).toBe(coupon.starts_at);
  expect(body.ends_at).toBe("2026-10-23T13:59:00.000Z");
  expect(saved).toHaveBeenCalledOnce();
});
test("voucher editor rejects an end before start without submitting", async () => {
  await render(
    <ResourceForm
      name="coupons"
      config={resources.coupons}
      record={coupon}
      onSaved={saved}
      onClose={() => {}}
    />,
  );
  await value(byLabel("Ngày kết thúc"), "2026-10-21");
  await submit();
  expect(api).not.toHaveBeenCalled();
  expect(container.textContent).toContain("kết thúc phải sau");
});
test("transfer form searches warehouse and product names but still sends foreign key IDs", async () => {
  all.mockImplementation(async (path) =>
    path.startsWith("warehouses/?scope=stock")
      ? [{ id: 1, name: "Kho chính", store_name: "Cầu Giấy" }]
      : path.startsWith("warehouses/")
        ? [{ id: 2, name: "Kho đích", store_name: "Thanh Xuân" }]
        : path.startsWith("variants/")
          ? [{ id: 77, sku: "SKU-ASUS", product_name: "Laptop ASUS" }]
          : [],
  );
  await render(
    <ResourceForm
      name="stock-transfers"
      config={resources["stock-transfers"]}
      record={null}
      onSaved={saved}
      onClose={() => {}}
    />,
  );
  async function choose(label, query, expected) {
    const input = byLabel(label);
    await act(async () => input.focus());
    await value(input, query);
    await act(async () =>
      [...container.querySelectorAll('[role="option"]')]
        .find((option) => option.textContent.includes(expected))
        .click(),
    );
  }
  await choose("Kho nguồn", "cau giay", "Cầu Giấy");
  await choose("Kho đích", "thanh xuan", "Thanh Xuân");
  await act(async () =>
    [...container.querySelectorAll("button")]
      .find((button) => button.textContent.includes("Thêm dòng"))
      .click(),
  );
  await choose("Sản phẩm dòng 1", "asus", "Laptop ASUS");
  await submit();
  expect(api).toHaveBeenCalledWith(
    "stock-transfers/",
    expect.objectContaining({
      body: expect.objectContaining({
        source: 1,
        destination: 2,
        items: [{ variant: 77, quantity: 1 }],
      }),
    }),
  );
});
