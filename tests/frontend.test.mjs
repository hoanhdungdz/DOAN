import test from "node:test";
import assert from "node:assert/strict";
import { operationKey } from "../shared/idempotency.js";
import { toMinorUnits, fromMinorUnits } from "../shared/money.js";
test("decimal line totals retain fractional units and large exact amounts", () => {
  assert.equal(fromMinorUnits(toMinorUnits("123.50") * 2n), "247.00");
  assert.equal(fromMinorUnits(toMinorUnits("0.10") * 3n), "0.30");
  assert.equal(
    fromMinorUnits(toMinorUnits("9007199254740993.99")),
    "9007199254740993.99",
  );
});
test("malformed currency is rejected rather than silently truncated", () => {
  assert.throws(() => toMinorUnits("12.345"));
  assert.throws(() => toMinorUnits("NaN"));
  assert.equal(fromMinorUnits(toMinorUnits("-12.50")), "-12.50");
});
test("same operation retains retry key, changed payload gets new key", () => {
  const keys = new Map(),
    payload = { order: 1, kind: "CAPTURE", reference: "bank-confirmation" };
  const first = operationKey(keys, "payment", payload);
  assert.equal(first, operationKey(keys, "payment", payload));
  assert.notEqual(
    first,
    operationKey(keys, "payment", { ...payload, reference: "changed" }),
  );
  assert.notEqual(first, operationKey(keys, "refund", payload));
});
