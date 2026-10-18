import React, { act } from "react";
import { createRoot } from "react-dom/client";
import { beforeEach, afterEach, test, expect } from "vitest";
import { ProductImage } from "./ui";
import { imageSources } from "./productImages";

globalThis.IS_REACT_ACT_ENVIRONMENT = true;
let container, root;
const source =
  "https://cdn2.cellphones.com.vn/200x/media/catalog/product/c/h/chuot-logitech-mx-master-3s.png";
beforeEach(() => {
  container = document.createElement("div");
  document.body.append(container);
  root = createRoot(container);
});
afterEach(async () => {
  await act(async () => root.unmount());
  container.remove();
});
async function fail() {
  await act(async () =>
    container.querySelector("img").dispatchEvent(new Event("error")),
  );
}

test("broken source URL uses local matching product, then reviewed remote, then an explicit unavailable image", async () => {
  await act(async () =>
    root.render(<ProductImage src={source} alt="MX Master 3S" />),
  );
  expect(container.querySelector("img").getAttribute("src")).toMatch(
    /^\/product-images\//,
  );
  await fail();
  expect(container.querySelector("img").getAttribute("src")).toBe(
    imageSources(source)[1],
  );
  expect(imageSources(source)[1]).not.toBe(source);
  await fail();
  expect(container.querySelector("img").dataset.imageState).toBe("unavailable");
  expect(container.querySelector("img").alt).toContain("Chưa có ảnh");
  await fail();
  expect(container.querySelector("img").getAttribute("src")).toBe(
    "/placeholder.svg",
  );
});

test("changing product after image failure resets the retry state", async () => {
  await act(async () =>
    root.render(<ProductImage src="/missing.png" alt="Old" />),
  );
  await fail();
  await act(async () => root.render(<ProductImage src={source} alt="New" />));
  expect(container.querySelector("img").getAttribute("src")).toMatch(
    /^\/product-images\//,
  );
  expect(container.querySelector("img").alt).toBe("New");
});

test("missing source is announced without an endless fallback loop", async () => {
  await act(async () => root.render(<ProductImage alt="Device" />));
  await fail();
  expect(container.querySelector("img").getAttribute("src")).toBe(
    "/placeholder.svg",
  );
  expect(container.querySelector("img").alt).toBe("Chưa có ảnh: Device");
});
