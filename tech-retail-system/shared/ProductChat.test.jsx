import React, { act } from "react";
import { createRoot } from "react-dom/client";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, afterEach, expect, test, vi } from "vitest";
import ProductChat from "../fe/src/components/ProductChat";
import { api } from "./api";
const session = vi.hoisted(() => ({ user: { id: 7 } }));
vi.mock("./session", () => ({ useSession: () => session }));
vi.mock("./api", async (original) => ({ ...(await original()), api: vi.fn() }));
globalThis.IS_REACT_ACT_ENVIRONMENT = true;
let root, container;
const response = {
  answer: "Cấu hình phù hợp nhu cầu.",
  mode: "rag",
  checked_at: "2026-10-22T04:00:00Z",
  products: [
    {
      id: 2,
      name: "Laptop ASUS Test",
      price: "1234000.00",
      path: "/products/asus-test",
      condition: "Mới",
      warranty_months: 24,
      image: "",
      stock: [{ store_name: "Cầu Giấy", available: 3 }],
    },
  ],
  sources: [
    {
      id: "product:1:0",
      title: "Thông số ASUS",
      excerpt: "RAM 16GB; không thực thi <script>alert(1)</script>",
    },
  ],
};
beforeEach(() => {
  session.user = { id: 7 };
  api.mockReset();
  api.mockImplementation((path) =>
    Promise.resolve(path === "features/" ? { gemini: true } : response),
  );
  container = document.createElement("div");
  document.body.append(container);
  root = createRoot(container);
});
afterEach(async () => {
  await act(async () => root.unmount());
  container.remove();
});
const button = (label) => container.querySelector(`[aria-label="${label}"]`);
async function render(path = "/products/asus-test") {
  await act(async () =>
    root.render(
      <MemoryRouter initialEntries={[path]}>
        <ProductChat />
      </MemoryRouter>,
    ),
  );
}
async function open() {
  await act(async () => button("Mở tư vấn AI").click());
}
async function send(question = "Laptop phù hợp?") {
  await act(async () => {
    const input = button("Câu hỏi tư vấn");
    Object.getOwnPropertyDescriptor(
      HTMLInputElement.prototype,
      "value",
    ).set.call(input, question);
    input.dispatchEvent(new Event("input", { bubbles: true }));
  });
  await act(async () =>
    container
      .querySelector("form")
      .dispatchEvent(new Event("submit", { bubbles: true, cancelable: true })),
  );
}

test("chat shows live server cards, citations, safe text and product context", async () => {
  await render();
  await open();
  await send();
  expect(api).toHaveBeenLastCalledWith(
    "ai/chat/",
    expect.objectContaining({
      body: {
        question: "Laptop phù hợp?",
        history: [],
        product_slug: "asus-test",
      },
      method: "POST",
    }),
  );
  expect(container.textContent).toContain("Cấu hình phù hợp nhu cầu.");
  expect(container.textContent).toContain("1.234.000");
  expect(
    container.querySelector('a[href="/products/asus-test"]'),
  ).not.toBeNull();
  expect(container.querySelector("script")).toBeNull();
  expect(container.querySelector(".chat-sources").textContent).toContain(
    "<script>",
  );
  await send("Còn mẫu nào?");
  expect(api.mock.calls.at(-1)[1].body.history).toEqual([
    { question: "Laptop phù hợp?" },
  ]);
});

test("clearing an in-flight question discards late replies and permits a new request", async () => {
  let resolve;
  api.mockImplementation((path) =>
    path === "features/"
      ? Promise.resolve({ gemini: true })
      : new Promise((done) => {
          resolve = done;
        }),
  );
  await render();
  await open();
  await send("Câu hỏi cũ");
  expect(container.textContent).toContain("Đang tìm dữ liệu");
  const signal = api.mock.calls.at(-1)[1].signal;
  await act(async () => button("Xóa hội thoại").click());
  expect(signal.aborted).toBe(true);
  await act(async () => resolve(response));
  expect(container.textContent).not.toContain("Cấu hình phù hợp nhu cầu.");
  expect(container.textContent).not.toContain("Câu hỏi cũ");
  expect(button("Câu hỏi tư vấn").disabled).toBe(false);
});

test("switching account clears chat and rejects late results from the previous account", async () => {
  let resolve;
  api.mockImplementation((path) =>
    path === "features/"
      ? Promise.resolve({ gemini: true })
      : new Promise((done) => {
          resolve = done;
        }),
  );
  await render();
  await open();
  await send("Tư vấn cho tài khoản cũ");
  session.user = { id: 8 };
  await render();
  await act(async () => resolve(response));
  expect(container.textContent).not.toContain("Tư vấn cho tài khoản cũ");
  expect(container.textContent).not.toContain("Cấu hình phù hợp nhu cầu.");
});

test("provider failures stay visible with explicit retry and no automatic repeat", async () => {
  api.mockImplementation((path) =>
    path === "features/"
      ? Promise.resolve({ gemini: true })
      : Promise.reject(new Error("AI tạm hết hạn mức")),
  );
  await render();
  await open();
  await send();
  expect(container.querySelector('[role="alert"]').textContent).toContain(
    "hết hạn mức",
  );
  expect(api.mock.calls.filter(([path]) => path === "ai/chat/")).toHaveLength(
    1,
  );
  expect(container.textContent).toContain("Thử lại câu hỏi");
});

test("catalog fallback shows its status, live cards and retains questions for followup", async () => {
  api.mockImplementation((path) =>
    Promise.resolve(
      path === "features/"
        ? { gemini: true }
        : {
            ...response,
            mode: "catalog",
            answer:
              "Dịch vụ AI đang tạm gián đoạn. Đây là kết quả lọc cơ bản từ danh mục.",
            sources: [],
            actions: [{ path: "/products", label: "Xem danh mục sản phẩm" }],
          },
    ),
  );
  await render("/products");
  await open();
  await send("laptop phù hợp cho sinh viên");
  expect(container.textContent).toContain(
    "Tra cứu danh mục · Tư vấn AI tạm ngừng",
  );
  expect(container.textContent).toContain("1.234.000");
  expect(container.querySelector('[role="alert"]')).toBeNull();
  expect(container.querySelector(".chat-sources")).toBeNull();
  expect(container.querySelector('a[href="/products"]')).not.toBeNull();
  expect(api.mock.calls.filter(([path]) => path === "ai/chat/")).toHaveLength(
    1,
  );
  await send("Dưới 20 triệu");
  expect(api).toHaveBeenLastCalledWith(
    "ai/chat/",
    expect.objectContaining({
      body: expect.objectContaining({
        history: [{ question: "laptop phù hợp cho sinh viên" }],
      }),
    }),
  );
});

test("disabled AI cannot send and only approved action and product paths become links", async () => {
  api.mockResolvedValue({ gemini: false });
  await render();
  await open();
  expect(button("Câu hỏi tư vấn").disabled).toBe(true);
  expect(container.textContent).toContain("Trợ lý chưa được bật");
  expect(api.mock.calls.filter(([path]) => path === "ai/chat/")).toHaveLength(
    0,
  );
});

test("private-order guidance links only to local approved destinations", async () => {
  api.mockImplementation((path) =>
    Promise.resolve(
      path === "features/"
        ? { gemini: true }
        : {
            answer: "Mở đơn của tôi",
            sources: [],
            products: [
              { ...response.products[0], path: "https://evil.invalid" },
            ],
            actions: [
              { path: "/orders", label: "Đơn hàng của tôi" },
              { path: "https://evil.invalid", label: "Bad" },
            ],
          },
    ),
  );
  await render("/products");
  await open();
  await send("Đơn của tôi đâu?");
  expect(container.querySelector('a[href="/orders"]')).not.toBeNull();
  expect(container.querySelector('a[href^="https:"]')).toBeNull();
});
