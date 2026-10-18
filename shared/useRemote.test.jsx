import React, { act } from "react";
import { createRoot } from "react-dom/client";
import { beforeEach, afterEach, test, expect, vi } from "vitest";
import { api } from "./api";
import useRemote from "./useRemote";
vi.mock("./api", () => ({ api: vi.fn(), errorText: (error) => error.message }));
globalThis.IS_REACT_ACT_ENVIRONMENT = true;
let container, root;
beforeEach(() => {
  api.mockReset();
  container = document.createElement("div");
  document.body.append(container);
  root = createRoot(container);
});
afterEach(async () => {
  await act(async () => root.unmount());
  container.remove();
});
function Screen({ path }) {
  const { data, loading, error } = useRemote(path);
  if (loading) return <p>loading</p>;
  if (error) return <p>{error}</p>;
  return (
    <p>
      {path === "list"
        ? `list:${data.results.length}`
        : `detail:${data.items.length}`}
    </p>
  );
}
test("list to detail transition never renders the previous response shape", async () => {
  api.mockResolvedValueOnce({ results: [{ id: 1 }] });
  await act(async () => root.render(<Screen path="list" />));
  expect(container.textContent).toBe("list:1");
  let resolveDetail;
  api.mockImplementationOnce(
    () =>
      new Promise((resolve) => {
        resolveDetail = resolve;
      }),
  );
  await act(async () => root.render(<Screen path="detail" />));
  expect(container.textContent).toBe("loading");
  await act(async () => resolveDetail({ items: [{}, {}] }));
  expect(container.textContent).toBe("detail:2");
});
test("a late response from the previous route cannot overwrite the current route", async () => {
  let resolveOld;
  api.mockImplementationOnce(
    () =>
      new Promise((resolve) => {
        resolveOld = resolve;
      }),
  );
  await act(async () => root.render(<Screen path="list" />));
  api.mockResolvedValueOnce({ items: [{}] });
  await act(async () => root.render(<Screen path="detail" />));
  expect(container.textContent).toBe("detail:1");
  await act(async () => resolveOld({ results: [{}, {}] }));
  expect(container.textContent).toBe("detail:1");
});
