"""Small-catalog exact vector index. Only public documents; atomic, rebuildable cache."""

import hashlib
import json
import os
from pathlib import Path
import tempfile
from threading import Lock
import unicodedata
from django.conf import settings
from django.utils.html import strip_tags
from common.errors import BusinessError
from apps.products.models import Product
from .provider import DIMENSIONS, normalized_vector

_lock = Lock()
KNOWLEDGE_DIR = Path(__file__).parent / "knowledge"
POLICIES = {"warranty": "Bảo hành và đổi lỗi", "checkout": "Đặt hàng và thanh toán"}


def normalize(text):
    text = unicodedata.normalize("NFD", str(text).lower().replace("đ", "d"))
    return "".join(c for c in text if unicodedata.category(c) != "Mn")


def chunks(text, size=1800, overlap=180):
    text = strip_tags(text).strip()
    for start in range(0, min(len(text), 12_000), size - overlap):
        yield text[start : start + size]


def documents():
    result = []

    def add(kind, ref, title, text):
        for part, content in enumerate(chunks(text)):
            ident = f"{kind}:{ref}:{part}"
            result.append(
                {
                    "id": ident,
                    "kind": kind,
                    "ref": ref,
                    "title": title,
                    "text": content,
                    "hash": hashlib.sha256((title + "\n" + content).encode()).hexdigest(),
                }
            )

    products = (
        Product.objects.filter(
            is_active=True,
            category__is_active=True,
            brand__is_active=True,
            variants__is_active=True,
        )
        .distinct()
        .select_related("category", "brand")
        .prefetch_related("specifications__definition", "variants")
        .order_by("pk")
    )
    for product in products:
        # Prices/stock, source_snapshot, feedback, identities and orders never enter the index.
        specs = (
            "\n".join(
                f"{spec.definition.name}: {spec.value} {spec.unit}"
                for spec in product.specifications.all()
            )
            or product.raw_specs
        )
        variants = "\n".join(
            f"SKU {v.sku}: {v.name}; tình trạng {v.condition}; bảo hành {v.warranty_months} tháng; "
            + json.dumps(v.attributes, ensure_ascii=False)
            for v in product.variants.all()
            if v.is_active
        )
        add(
            "product",
            product.pk,
            product.name,
            f"{product.name}\nDanh mục: {product.category.name}\nHãng: {product.brand.name}\n"
            f"{specs}\n{variants}",
        )
    for ref, title in POLICIES.items():
        add("policy", ref, title, (KNOWLEDGE_DIR / f"{ref}.md").read_text(encoding="utf-8"))
    return result


def signature():
    return {"version": 2, "model": settings.GEMINI_EMBEDDING_MODEL, "dimensions": DIMENSIONS}


def load_index():
    try:
        path = Path(settings.RAG_INDEX_PATH)
        if path.stat().st_size > 40_000_000:
            return {}
        data = json.loads(path.read_text(encoding="utf-8"))
        if data.get("signature") != signature() or not isinstance(data.get("rows"), dict):
            return {}
        if any(not isinstance(row, dict) for row in data["rows"].values()):
            return {}
        return data["rows"]
    except OSError, ValueError, TypeError, AttributeError:
        return {}


def _save(rows):
    temporary = None
    try:
        path = Path(settings.RAG_INDEX_PATH)
        path.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", dir=path.parent, suffix=".tmp", delete=False
        ) as handle:
            temporary = handle.name
            json.dump({"signature": signature(), "rows": rows}, handle, ensure_ascii=False)
        os.replace(temporary, path)
    except OSError:
        raise BusinessError("Chưa lưu được chỉ mục tư vấn.", "AI_INDEX_UNAVAILABLE", 503) from None
    finally:
        if temporary:
            Path(temporary).unlink(missing_ok=True)


def sync_index(docs, provider, *, rebuild=False, progress=None):
    if not _lock.acquire(blocking=False):
        raise BusinessError(
            "Dữ liệu tư vấn đang cập nhật. Vui lòng thử lại sau.", "AI_INDEX_BUSY", 503
        )
    try:
        old = {} if rebuild else load_index()
        rows, pending = {}, []
        for doc in docs:
            previous = old.get(doc["id"], {})
            if previous.get("hash") == doc["hash"]:
                try:
                    rows[doc["id"]] = {**doc, "vector": normalized_vector(previous.get("vector"))}
                    continue
                except BusinessError:
                    pass
            pending.append(doc)
        for start in range(0, len(pending), 12):
            batch = pending[start : start + 12]
            vectors = provider.embed(
                [f"title: {doc['title']} | text: {doc['text']}" for doc in batch]
            )
            if len(vectors) != len(batch):
                raise BusinessError("Chỉ mục tìm kiếm chưa đầy đủ.", "AI_INVALID_RESPONSE", 503)
            for doc, vector in zip(batch, vectors, strict=True):
                rows[doc["id"]] = {**doc, "vector": normalized_vector(vector)}
            # Resume successful batches after a quota interruption without paying to embed again.
            _save(rows)
            if progress:
                progress(min(start + len(batch), len(pending)), len(pending))
        if not pending and (set(old) != set(rows) or rebuild):
            _save(rows)
        return list(rows.values()), len(pending)
    finally:
        _lock.release()
