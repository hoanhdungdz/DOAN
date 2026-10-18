"""Read every source row; report observed facts without modifying the dataset."""

import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path

parser = argparse.ArgumentParser()
parser.add_argument(
    "--file", default=str(Path(__file__).resolve().parents[1] / "be/data/final_master_dataset.json")
)
parser.add_argument(
    "--output", default=str(Path(__file__).resolve().parents[1] / "docs/data-analysis.json")
)
args = parser.parse_args()
path = Path(args.file)
raw = path.read_bytes()
rows = json.loads(raw)
keys = set().union(*(r.keys() for r in rows))
report = {
    "source_file": path.name,
    "sha256": hashlib.sha256(raw).hexdigest(),
    "count": len(rows),
    "categories": dict(Counter(r["category"] for r in rows)),
    "brands": sorted({" ".join(r["brand"].split()) for r in rows}),
    "field_counts": dict(Counter(len(r) for r in rows)),
    "types": {k: dict(Counter(type(r.get(k)).__name__ for r in rows)) for k in sorted(keys)},
    "missing": {k: sum(k not in r for r in rows) for k in sorted(keys)},
    "nulls": {k: sum(r.get(k) is None for r in rows) for k in sorted(keys)},
    "empty_strings": {k: sum(r.get(k) == "" for r in rows) for k in sorted(keys)},
    "duplicates": {
        k: {str(v): n for v, n in Counter(r[k] for r in rows).items() if n > 1}
        for k in ["id", "sku", "slug", "url", "source_url"]
    },
    "stock": sum(r["total_stock"] for r in rows),
    "stores": {
        s: sum(r["inventory"].get(s, 0) for r in rows)
        for s in sorted(set().union(*(r["inventory"].keys() for r in rows)))
    },
    "stock_mismatch": [r["id"] for r in rows if sum(r["inventory"].values()) != r["total_stock"]],
    "conditions": dict(Counter(r["condition"] for r in rows)),
    "prices": [min(r["price"] for r in rows), max(r["price"] for r in rows)],
    "brand_whitespace": [
        (r["id"], r["brand"]) for r in rows if r["brand"] != " ".join(r["brand"].split())
    ],
}
Path(args.output).write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
print(
    f"Analyzed {len(rows)} rows; {len(report['brands'])} brands; stock {report['stock']}; duplicate slug groups {len(report['duplicates']['slug'])}."
)
