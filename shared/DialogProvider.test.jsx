import React, { act, useState } from "react";
import { createRoot } from "react-dom/client";
import { beforeEach, afterEach, test, expect } from "vitest";
import DialogProvider from "./DialogProvider";
import { confirmAction } from "./dialogs";
globalThis.IS_REACT_ACT_ENVIRONMENT = true;
let container, root;
beforeEach(() => {
  container = document.createElement("div");
  document.body.append(container);
  root = createRoot(container);
});
afterEach(async () => {
  await act(async () => root.unmount());
  container.remove();
});
function Operation() {
  const [result, setResult] = useState("idle");
  return (
    <>
      <button
        onClick={async () =>
          setResult(
            (await confirmAction("Ghi sổ chứng từ test?"))
              ? "confirmed"
              : "cancelled",
          )
        }
      >
        Thực hiện
      </button>
      <p>{result}</p>
    </>
  );
}
async function open() {
  await act(async () =>
    root.render(
      <DialogProvider>
        <Operation />
      </DialogProvider>,
    ),
  );
  await act(async () => container.querySelector("button").click());
}
test("confirmation is an accessible in-app dialog and resolves only after confirming", async () => {
  await open();
  const dialog = document.querySelector('[role="dialog"]');
  expect(dialog.getAttribute("aria-modal")).toBe("true");
  expect(container.textContent).toContain("idle");
  await act(async () => dialog.querySelector(".primary").click());
  expect(container.textContent).toContain("confirmed");
  expect(document.querySelector('[role="dialog"]')).toBeNull();
});
test("cancelling a confirmation prevents the operation", async () => {
  await open();
  await act(async () =>
    document.querySelector('[role="dialog"] button[type="button"]').click(),
  );
  expect(container.textContent).toContain("cancelled");
});
