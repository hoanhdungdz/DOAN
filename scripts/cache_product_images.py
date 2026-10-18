"""Build local catalog assets from source URLs and reviewed image corrections."""

import concurrent.futures
import hashlib
import json
from pathlib import Path
from urllib.parse import urlsplit
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parent.parent
PUBLIC = ROOT / "shared" / "public"
ASSETS = PUBLIC / "product-images"
MIME_EXTENSIONS = {"image/png": ".png", "image/jpeg": ".jpg", "image/webp": ".webp"}
HOSTS = {"cdn2.cellphones.com.vn", "assets3.razerzone.com", "cdn.shopify.com"}


def download(url):
    parsed = urlsplit(url)
    if parsed.scheme != "https" or parsed.hostname not in HOSTS:
        raise ValueError("Unapproved catalog image host")
    with urlopen(Request(url, headers={"User-Agent": "Mozilla/5.0"}), timeout=25) as r:
        if urlsplit(r.url).hostname not in HOSTS:
            raise ValueError("Unapproved image redirect")
        mime = r.headers.get_content_type()
        data = r.read(8 * 1024 * 1024 + 1)
    if mime not in MIME_EXTENSIONS or not data or len(data) > 8 * 1024 * 1024:
        raise ValueError("Invalid or oversized image response")
    valid = (
        data.startswith(b"\x89PNG\r\n\x1a\n")
        or data.startswith(b"\xff\xd8\xff")
        or (data[:4] == b"RIFF" and data[8:12] == b"WEBP")
    )
    if not valid:
        raise ValueError("Response is not a supported raster image")
    return data, MIME_EXTENSIONS[mime]


def main():
    rows = json.loads((ROOT / "be/data/final_master_dataset.json").read_text("utf-8"))
    overrides = json.loads((ROOT / "shared/product-image-overrides.json").read_text("utf-8"))
    ASSETS.mkdir(parents=True, exist_ok=True)

    def cache(source):
        resolved = overrides.get(source, {}).get("url", source)
        # Prefer a sharper copy of the identical CDN asset, then its original size.
        large = resolved.replace("/200x/media/", "/600x/media/")
        try:
            data, extension = download(large)
            fetched = large
        except Exception:
            data, extension = download(resolved)
            fetched = resolved
        digest = hashlib.sha256(data).hexdigest()
        filename = digest[:24] + extension
        (ASSETS / filename).write_bytes(data)
        return source, {
            "local": "/product-images/" + filename,
            "remote": resolved,
            "fetched": fetched,
            "sha256": digest,
            "bytes": len(data),
        }

    sources = sorted({row["image"] for row in rows if row["image"]})
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
        manifest = dict(pool.map(cache, sources))
    target = ROOT / "shared/product-images.json"
    temporary = target.with_suffix(".tmp")
    temporary.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", "utf-8")
    temporary.replace(target)
    index = {source: entry["local"] for source, entry in manifest.items()}
    (ROOT / "shared/product-image-index.json").write_text(
        json.dumps(index, ensure_ascii=False, indent=2) + "\n", "utf-8"
    )
    print(
        json.dumps(
            {"products": len(rows), "images": len(manifest), "corrected_urls": len(overrides)}
        )
    )


if __name__ == "__main__":
    main()
