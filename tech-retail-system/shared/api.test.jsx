import { afterEach, beforeEach, expect, test, vi } from "vitest";

let api, fetchMock;
const jsonResponse = (data, status = 200) => ({
  ok: status >= 200 && status < 300,
  status,
  json: async () => data,
});
const tokenResponse = (token) => jsonResponse({ csrfToken: token });
beforeEach(async () => {
  vi.resetModules();
  fetchMock = vi.fn();
  vi.stubGlobal("fetch", fetchMock);
  ({ api } = await import("./api"));
});
afterEach(() => vi.unstubAllGlobals());

test("each mutation uses a fresh token after another tab rotates the cookie", async () => {
  fetchMock
    .mockResolvedValueOnce(tokenResponse("before-login"))
    .mockResolvedValueOnce(jsonResponse({ message: "first" }))
    .mockResolvedValueOnce(tokenResponse("after-login-elsewhere"))
    .mockResolvedValueOnce(jsonResponse({ message: "second" }));
  await api("my-orders/12/cancel/", { method: "POST", body: { code: "one" } });
  await api("my-orders/12/cancel/", { method: "post", body: { code: "two" } });
  expect(fetchMock).toHaveBeenCalledTimes(4);
  expect(fetchMock.mock.calls[0][1].cache).toBe("no-store");
  expect(fetchMock.mock.calls[1][1].headers.get("X-CSRFToken")).toBe(
    "before-login",
  );
  expect(fetchMock.mock.calls[3][1].headers.get("X-CSRFToken")).toBe(
    "after-login-elsewhere",
  );
  expect(fetchMock.mock.calls[3][1].method).toBe("POST");
});

test("a CSRF rejection retries once with fresh token and identical operation key/body", async () => {
  fetchMock
    .mockResolvedValueOnce(tokenResponse("old"))
    .mockResolvedValueOnce(
      jsonResponse({ code: "CSRF_FAILED", message: "stale" }, 403),
    )
    .mockResolvedValueOnce(tokenResponse("fresh"))
    .mockResolvedValueOnce(jsonResponse({ id: 123 }));
  const result = await api("orders/", {
    method: "POST",
    body: { quantity: 2 },
    headers: {
      "Idempotency-Key": "same-operation",
      "x-csrftoken": "caller-stale-token",
    },
  });
  expect(result).toEqual({ id: 123 });
  const first = fetchMock.mock.calls[1][1],
    retry = fetchMock.mock.calls[3][1];
  expect(first.headers.get("X-CSRFToken")).toBe("old");
  expect(retry.headers.get("X-CSRFToken")).toBe("fresh");
  expect(first.headers.get("Idempotency-Key")).toBe(
    retry.headers.get("Idempotency-Key"),
  );
  expect(first.body).toBe(retry.body);
  expect(retry.credentials).toBe("include");
});

test.each([400, 401, 403, 409, 429, 500])(
  "ordinary HTTP %i failures are never replayed",
  async (status) => {
    fetchMock
      .mockResolvedValueOnce(tokenResponse("valid"))
      .mockResolvedValueOnce(
        jsonResponse(
          { code: "BUSINESS_OR_PERMISSION_ERROR", message: "blocked" },
          status,
        ),
      );
    await expect(
      api("orders/", { method: "POST", body: {} }),
    ).rejects.toMatchObject({ status, code: "BUSINESS_OR_PERMISSION_ERROR" });
    expect(fetchMock).toHaveBeenCalledTimes(2);
  },
);

test("repeated CSRF failure stops after a single retry", async () => {
  fetchMock
    .mockResolvedValueOnce(tokenResponse("first"))
    .mockResolvedValueOnce(
      jsonResponse({ code: "CSRF_FAILED", message: "stale" }, 403),
    )
    .mockResolvedValueOnce(tokenResponse("second"))
    .mockResolvedValueOnce(
      jsonResponse({ code: "CSRF_FAILED", message: "still stale" }, 403),
    );
  await expect(
    api("my-orders/12/cancel/", { method: "POST", body: {} }),
  ).rejects.toMatchObject({ code: "CSRF_FAILED", status: 403 });
  expect(fetchMock).toHaveBeenCalledTimes(4);
});

test("concurrent mutations share the pending token request", async () => {
  let finishRefresh;
  const refresh = new Promise((resolve) => {
    finishRefresh = resolve;
  });
  fetchMock.mockImplementation((url) =>
    url.endsWith("auth/csrf/")
      ? refresh
      : Promise.resolve(jsonResponse({ ok: true })),
  );
  const first = api("carts/", { method: "PUT", body: { items: [] } });
  const second = api("my-orders/12/cancel/", { method: "POST", body: {} });
  expect(fetchMock).toHaveBeenCalledTimes(1);
  finishRefresh(tokenResponse("shared"));
  await Promise.all([first, second]);
  expect(fetchMock).toHaveBeenCalledTimes(3);
  for (const [, options] of fetchMock.mock.calls.slice(1)) {
    expect(options.headers.get("X-CSRFToken")).toBe("shared");
  }
});

test("failed token initialization can recover on the next user attempt", async () => {
  fetchMock
    .mockResolvedValueOnce(jsonResponse({ message: "unavailable" }, 503))
    .mockResolvedValueOnce(tokenResponse("recovered"))
    .mockResolvedValueOnce(jsonResponse({ ok: true }));
  await expect(
    api("carts/", { method: "PUT", body: {} }),
  ).rejects.toMatchObject({ status: 503 });
  await expect(api("carts/", { method: "PUT", body: {} })).resolves.toEqual({
    ok: true,
  });
  expect(fetchMock).toHaveBeenCalledTimes(3);
});

test("network failures do not replay a write that may have been processed", async () => {
  fetchMock
    .mockResolvedValueOnce(tokenResponse("valid"))
    .mockRejectedValueOnce(new TypeError("connection lost"));
  await expect(api("orders/", { method: "POST", body: {} })).rejects.toThrow(
    "connection lost",
  );
  expect(fetchMock).toHaveBeenCalledTimes(2);
});

test("read-only requests do not bootstrap CSRF", async () => {
  fetchMock.mockResolvedValueOnce(jsonResponse({ results: [] }));
  await api("products/");
  expect(fetchMock).toHaveBeenCalledTimes(1);
  expect(fetchMock.mock.calls[0][1].headers.has("X-CSRFToken")).toBe(false);
});

test("multipart feedback keeps browser boundary, cookies and fresh CSRF without serializing files", async () => {
  fetchMock
    .mockResolvedValueOnce(tokenResponse("multipart-token"))
    .mockResolvedValueOnce(jsonResponse({ id: 1 }));
  const body = new FormData();
  body.append("body", "Nội dung đánh giá");
  body.append(
    "photos",
    new File(["image"], "photo.jpg", { type: "image/jpeg" }),
  );
  await api("products/item/feedback/", { method: "POST", body });
  const sent = fetchMock.mock.calls[1][1];
  expect(sent.body).toBe(body);
  expect(sent.headers.has("Content-Type")).toBe(false);
  expect(sent.headers.get("X-CSRFToken")).toBe("multipart-token");
  expect(sent.credentials).toBe("include");
});
