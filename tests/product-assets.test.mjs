import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { createHash } from "node:crypto";
const read = (path) =>
  JSON.parse(readFileSync(new URL(path, import.meta.url), "utf8"));
test("every source product has a complete local image with the recorded content hash", () => {
  const rows = read("../be/data/final_master_dataset.json");
  const manifest = read("../shared/product-images.json");
  const index = read("../shared/product-image-index.json");
  assert.equal(rows.length, 278);
  for (const row of rows) {
    const entry = manifest[row.image];
    assert.ok(entry, row.id);
    assert.equal(index[row.image], entry.local);
    assert.match(
      entry.local,
      /^\/product-images\/[a-f0-9]{24}\.(png|jpg|webp)$/,
    );
    const bytes = readFileSync(
      new URL("../shared/public" + entry.local, import.meta.url),
    );
    assert.equal(bytes.length, entry.bytes);
    assert.equal(
      createHash("sha256").update(bytes).digest("hex"),
      entry.sha256,
    );
  }
});
