import React, { act } from "react";
import { createRoot } from "react-dom/client";
import { MemoryRouter } from "react-router-dom";
import { afterEach, beforeEach, expect, test, vi } from "vitest";
import ProductCommunity from "../fe/src/components/ProductCommunity";
import FeedbackPage from "../admin/src/pages/FeedbackPage";
import { api } from "./api";

const session = vi.hoisted(() => ({ user: null }));
vi.mock("./session", () => ({ useSession: () => session }));
vi.mock("./api", async (original) => ({ ...(await original()), api: vi.fn() }));
globalThis.IS_REACT_ACT_ENVIRONMENT = true;
let container, root, feed;
const product = { id: 1, slug: "test-product" };
const item = (extra = {}) => ({
  id: 12,
  kind: "QUESTION",
  author: "Người gửi thực",
  title: "",
  body: "Máy có hỗ trợ màn hình ngoài không?",
  rating: null,
  status: "APPROVED",
  is_mine: false,
  verified_purchase: false,
  created_at: "2026-10-21T10:00:00Z",
  photos: [],
  helpful_count: 0,
  helpful: false,
  replies: [],
  ...extra,
});
beforeEach(() => {
  container = document.createElement("div");
  document.body.append(container);
  root = createRoot(container);
  session.user = null;
  feed = {
    count: 0,
    results: [],
    summary: {
      count: 0,
      average: null,
      distribution: { 1: 0, 2: 0, 3: 0, 4: 0, 5: 0 },
      questions: 0,
    },
    viewer: { can_review: false, review_status: null, authenticated: false },
  };
  api.mockReset();
  api.mockImplementation(async () => feed);
});
afterEach(async () => {
  await act(async () => root.unmount());
  container.remove();
});
const render = () =>
  act(async () =>
    root.render(
      <MemoryRouter>
        <ProductCommunity product={product}>
          <p>Thông số hiện có</p>
        </ProductCommunity>
      </MemoryRouter>,
    ),
  );
const button = (text) =>
  [...container.querySelectorAll("button")].find((b) =>
    b.textContent.includes(text),
  );
async function fill(selector, value) {
  await act(async () => {
    const input = container.querySelector(selector);
    Object.getOwnPropertyDescriptor(
      input.tagName === "TEXTAREA"
        ? HTMLTextAreaElement.prototype
        : HTMLInputElement.prototype,
      "value",
    ).set.call(input, value);
    input.dispatchEvent(new Event("input", { bubbles: true }));
  });
}
async function submit(selector = ".review-form") {
  await act(async () =>
    container
      .querySelector(selector)
      .dispatchEvent(new Event("submit", { bubbles: true, cancelable: true })),
  );
}

test("empty interface shows no fabricated users, stars, reviews or questions and retains product specs", async () => {
  await render();
  expect(container.textContent).toContain("Chưa có đánh giá");
  expect(container.textContent).not.toMatch(
    /4,8|Hoàng Minh|Thu Hà|28 đánh giá/,
  );
  expect(container.querySelector(".rating-overview strong").textContent).toBe(
    "—/5",
  );
  expect(container.querySelector(".review-form")).toBeNull();
  await act(async () => button("Hỏi đáp").click());
  expect(container.textContent).toContain("Chưa có câu hỏi");
  expect(container.querySelector(".question-form")).toBeNull();
  await act(async () => button("Thông số").click());
  expect(container.textContent).toContain("Thông số hiện có");
});
test("section tabs support keyboard navigation and expose the active panel", async () => {
  await render();
  await act(async () =>
    container.querySelector("#community-tab-REVIEW").dispatchEvent(
      new KeyboardEvent("keydown", {
        key: "ArrowRight",
        bubbles: true,
        cancelable: true,
      }),
    ),
  );
  expect(
    container
      .querySelector("#community-tab-QUESTION")
      .getAttribute("aria-selected"),
  ).toBe("true");
  expect(
    container
      .querySelector('[role="tabpanel"]')
      .getAttribute("aria-labelledby"),
  ).toBe("community-tab-QUESTION");
  expect(container.querySelector("#community-tab-REVIEW").tabIndex).toBe(-1);
});

test("unverified customer cannot see the review composer or claim a purchase", async () => {
  session.user = { id: 2 };
  await render();
  expect(container.querySelector(".review-form")).toBeNull();
  expect(container.textContent).not.toContain("Bạn đã mua sản phẩm này");
  expect(container.textContent).toContain("sau khi đơn hàng");
});
test("verified customer submits rating text and photos as multipart and sees moderation status", async () => {
  session.user = { id: 1 };
  feed.viewer = { can_review: true, review_status: null };
  await render();
  await act(async () =>
    container.querySelector('button[aria-label="5 sao"]').click(),
  );
  await fill(".review-form textarea", "Trải nghiệm sử dụng thực tế rất tốt.");
  const upload = container.querySelector('input[type="file"]');
  const image = new File(["image"], "review.jpg", { type: "image/jpeg" });
  await act(async () => {
    Object.defineProperty(upload, "files", {
      value: [image],
      configurable: true,
    });
    upload.dispatchEvent(new Event("change", { bubbles: true }));
  });
  const original = api.getMockImplementation();
  api.mockImplementation(async (path, options) => {
    if (options?.method === "POST") {
      feed = {
        ...feed,
        viewer: { can_review: false, review_status: "PENDING" },
      };
      return { id: 10, status: "PENDING" };
    }
    return original(path, options);
  });
  await submit();
  const call = api.mock.calls.find(([, options]) => options?.method === "POST");
  expect(call[0]).toBe("products/test-product/feedback/");
  expect(call[1].body).toBeInstanceOf(FormData);
  expect(call[1].body.get("rating")).toBe("5");
  expect(call[1].body.get("kind")).toBe("REVIEW");
  expect(call[1].body.getAll("photos")).toHaveLength(1);
  expect(container.textContent).toContain("Đang chờ duyệt");
  expect(container.querySelector(".rating-overview strong").textContent).toBe(
    "—/5",
  );
});
test("review cannot submit without stars and network failures keep the draft for retry", async () => {
  session.user = { id: 1 };
  feed.viewer.can_review = true;
  await render();
  await fill(".review-form textarea", "Nội dung đánh giá cần giữ lại.");
  await submit();
  expect(container.textContent).toContain("Vui lòng chọn số sao");
  await act(async () =>
    container.querySelector('button[aria-label="4 sao"]').click(),
  );
  api.mockRejectedValueOnce(new Error("Mất kết nối"));
  await submit();
  expect(container.textContent).toContain("Mất kết nối");
  expect(container.querySelector(".review-form textarea").value).toContain(
    "cần giữ lại",
  );
  expect(button("Gửi đánh giá").disabled).toBe(false);
});
test("questions do not require a purchase and replies cannot attach a staff badge", async () => {
  session.user = { id: 2 };
  feed.results = [item()];
  feed.count = 1;
  feed.summary.questions = 1;
  await render();
  await act(async () => button("Hỏi đáp").click());
  expect(container.querySelector(".question-form")).not.toBeNull();
  await act(async () => button("Trả lời").click());
  await fill(".community-inline-form textarea", "Tôi cũng cần tư vấn thêm.");
  await submit(".community-inline-form");
  expect(api).toHaveBeenCalledWith("feedback/12/replies/", {
    method: "POST",
    body: { body: "Tôi cũng cần tư vấn thêm." },
  });
});
test("only server-marked staff replies get the staff badge and text is escaped", async () => {
  feed.results = [
    item({
      body: '<img src=x onerror="alert(1)">',
      replies: [
        {
          id: 2,
          author: "TechRetail",
          body: "Tư vấn từ cửa hàng",
          is_staff_reply: true,
          status: "APPROVED",
        },
      ],
    }),
  ];
  feed.count = 1;
  await render();
  expect(container.querySelector(".community-thread img")).toBeNull();
  expect(container.querySelector(".community-thread").textContent).toContain(
    "<img src=x",
  );
  expect(
    container.querySelector(".community-reply.staff").textContent,
  ).toContain("Nhân viên");
});
test("an account switch discards a pending review submission and its draft", async () => {
  session.user = { id: 1 };
  feed.viewer.can_review = true;
  await render();
  await act(async () =>
    container.querySelector('button[aria-label="5 sao"]').click(),
  );
  await fill(".review-form textarea", "Bản nháp riêng của tài khoản A.");
  let finish;
  api.mockImplementationOnce(
    () =>
      new Promise((resolve) => {
        finish = resolve;
      }),
  );
  await submit();
  session.user = { id: 2 };
  feed.viewer.can_review = false;
  await render();
  await act(async () => finish({ id: 10, status: "PENDING" }));
  expect(container.textContent).not.toContain("Bản nháp riêng");
  expect(container.textContent).not.toContain("Đã gửi đánh giá");
});
test("admin page refuses customers and does not fetch the moderation API", async () => {
  session.user = { id: 1, is_admin: false };
  await act(async () =>
    root.render(
      <MemoryRouter>
        <FeedbackPage />
      </MemoryRouter>,
    ),
  );
  expect(container.textContent).toContain("Chỉ quản trị viên");
  expect(api).not.toHaveBeenCalled();
});
test("admin approves actual pending content and sends an official reply through API", async () => {
  session.user = { id: 9, is_admin: true };
  feed.results = [
    item({ status: "PENDING", product_name: "Sản phẩm thực", reports: [] }),
  ];
  feed.count = 1;
  await act(async () =>
    root.render(
      <MemoryRouter>
        <FeedbackPage />
      </MemoryRouter>,
    ),
  );
  await act(async () => button("Duyệt hiển thị").click());
  expect(api).toHaveBeenCalledWith("feedback-admin/12/", {
    method: "PATCH",
    body: { status: "APPROVED" },
  });
  await fill(
    ".feedback-moderation-card textarea",
    "Chào bạn, shop xin hỗ trợ.",
  );
  await submit(".feedback-moderation-card form");
  expect(api).toHaveBeenCalledWith("feedback/12/replies/", {
    method: "POST",
    body: { body: "Chào bạn, shop xin hỗ trợ." },
  });
});
