import json
import re
from collections import Counter
from decimal import Decimal
from pathlib import Path
from urllib.parse import urlparse
from django.db import transaction
from django.utils.text import slugify
from common.errors import BusinessError
from apps.stores.models import Store, Warehouse
from apps.inventory.models import InventoryBalance, StockMovement
from .models import (
    Category,
    Brand,
    Product,
    ProductVariant,
    ProductImage,
    SpecificationDefinition,
    ProductSpecification,
)

CATEGORIES = {
    "Laptop": "Laptop",
    "Dien_thoai": "Điện thoại",
    "Gia_dung_Smarthome": "Gia dụng & Smarthome",
    "May_tinh_bang": "Máy tính bảng",
    "Phu_kien_Cong_nghe": "Phụ kiện công nghệ",
    "Man_hinh_PC": "Màn hình PC",
    "Am_thanh_Smartwatch": "Âm thanh & Smartwatch",
}
FIELDS = {
    "id",
    "category",
    "name",
    "brand",
    "price",
    "description",
    "image",
    "url",
    "specs",
    "condition",
    "warranty_months",
    "inventory",
    "total_stock",
    "sku",
    "slug",
    "source_url",
}


def normalize(value):
    return " ".join(value.split())


def validate_dataset(path):
    rows = json.loads(Path(path).read_text(encoding="utf-8-sig"))
    if not isinstance(rows, list) or not rows:
        raise BusinessError("Dataset phải là danh sách không rỗng.", "INVALID_DATASET", 400)
    errors = []
    seen_id = set()
    seen_sku = set()
    for index, r in enumerate(rows):
        prefix = f"[{index}]"
        if not isinstance(r, dict) or not FIELDS.issubset(r):
            errors.append(f"{prefix}: thiếu trường bắt buộc")
            continue
        for k in FIELDS - {"price", "warranty_months", "total_stock", "inventory"}:
            if not isinstance(r[k], str):
                errors.append(f"{prefix}.{k}: cần chuỗi")
        for k in ["id", "name", "sku", "slug", "brand", "category", "condition"]:
            if not isinstance(r[k], str) or not normalize(r[k]):
                errors.append(f"{prefix}.{k}: không được rỗng")
        for k in ["price", "warranty_months", "total_stock"]:
            if type(r[k]) is not int or r[k] < 0:
                errors.append(f"{prefix}.{k}: cần số nguyên không âm")
        inv = r["inventory"]
        if (
            not isinstance(inv, dict)
            or not inv
            or any(
                not isinstance(s, str) or not normalize(s) or type(q) is not int or q < 0
                for s, q in inv.items()
            )
        ):
            errors.append(f"{prefix}.inventory: dữ liệu không hợp lệ")
        elif sum(inv.values()) != r["total_stock"]:
            errors.append(f"{prefix}.total_stock: không khớp inventory")
        for k in ["id", "sku"]:
            seen = seen_id if k == "id" else seen_sku
            if isinstance(r[k], str):
                if r[k] in seen:
                    errors.append(f"{prefix}.{k}: trùng {r[k]}")
                seen.add(r[k])
        for k in ["image", "source_url"]:
            if isinstance(r[k], str) and r[k] and urlparse(r[k]).scheme not in ("https", "http"):
                errors.append(f"{prefix}.{k}: URL không hợp lệ")
        for k, limit in {
            "id": 80,
            "sku": 100,
            "name": 500,
            "brand": 150,
            "category": 100,
            "condition": 100,
            "slug": 500,
            "image": 1500,
            "source_url": 1000,
        }.items():
            if isinstance(r[k], str) and len(r[k]) > limit:
                errors.append(f"{prefix}.{k}: quá dài ({limit})")
    if errors:
        raise BusinessError("\n".join(errors), "INVALID_DATASET", 400)
    return rows


def parse_specs(text):
    for part in text.split(" | "):
        if ":" not in part:
            continue
        name, value = part.split(":", 1)
        name = normalize(name)
        value = value.strip()
        if not name or not value:
            continue
        match = re.fullmatch(r"(\d+(?:\.\d+)?)\s*(GB|TB|MB|inches|inch|Hz|mAh|W|kg|g)", value, re.I)
        yield name[:200], value, Decimal(match[1]) if match else None, match[2] if match else ""


@transaction.atomic
def import_dataset(path, dry_run=False, review=True):
    rows = validate_dataset(path)
    counts = {
        "source": len(rows),
        "create": 0,
        "update": 0,
        "skip": 0,
        "error": 0,
        "initial_stock": 0,
    }
    slug_counts = Counter(r["slug"] for r in rows)
    changed_source_ids = set()
    # Preflight every identity conflict before writing anything, including dry runs.
    for r in rows:
        existing = Product.objects.filter(
            source_namespace="master_dataset", source_id=r["id"]
        ).first()
        sku = ProductVariant.objects.filter(sku=r["sku"]).first()
        if (sku and (not existing or sku.product_id != existing.pk)) or (
            existing
            and existing.variants.exists()
            and not existing.variants.filter(sku=r["sku"]).exists()
        ):
            raise BusinessError(f"{r['id']}: SKU xung đột identity", "SOURCE_CONFLICT")
    for r in rows:
        category, _ = Category.objects.get_or_create(
            source_key=normalize(r["category"]),
            defaults={"name": CATEGORIES.get(r["category"], normalize(r["category"]))},
        )
        brand, _ = Brand.objects.get_or_create(name=normalize(r["brand"]))
        base = slugify(r["slug"])[:210] or slugify(r["id"])
        slug = f"{base}-{r['id'].lower()}" if slug_counts[r["slug"]] > 1 else base
        owner = (
            Product.objects.filter(slug=slug)
            .exclude(source_namespace="master_dataset", source_id=r["id"])
            .first()
        )
        if owner:
            slug = f"{base}-{r['id'].lower()}"
        if (
            Product.objects.filter(slug=slug)
            .exclude(source_namespace="master_dataset", source_id=r["id"])
            .exists()
        ):
            raise BusinessError(f"{r['id']}: slug xung đột", "SLUG_CONFLICT")
        product, created = Product.objects.get_or_create(
            source_namespace="master_dataset",
            source_id=r["id"],
            defaults={"name": r["name"], "category": category, "brand": brand, "slug": slug},
        )
        same = not created and product.source_snapshot == r
        counts["create" if created else "skip" if same else "update"] += 1
        if not same:
            changed_source_ids.add(r["id"])
            for field, value in {
                "name": r["name"],
                "category": category,
                "brand": brand,
                "description": r["description"],
                "raw_specs": r["specs"],
                "source_snapshot": r,
                "original_slug": r["slug"],
                "source_url": r["source_url"],
            }.items():
                setattr(product, field, value)
            product.save()
            product.images.all().delete()
            if r["image"]:
                ProductImage.objects.create(product=product, url=r["image"])
            product.specifications.all().delete()
            for name, value, numeric, unit in parse_specs(r["specs"]):
                definition, _ = SpecificationDefinition.objects.get_or_create(name=name)
                ProductSpecification.objects.create(
                    product=product,
                    definition=definition,
                    value=value,
                    numeric_value=numeric,
                    unit=unit,
                )
        variant, _ = ProductVariant.objects.get_or_create(
            product=product,
            sku=r["sku"],
            defaults={
                "price": Decimal(r["price"]),
                "condition": r["condition"],
                "warranty_months": r["warranty_months"],
            },
        )
        # Never overwrite an operational price or inventory on reimport.
        if created:
            for store_name, quantity in sorted(r["inventory"].items()):
                store, _ = Store.objects.get_or_create(name=normalize(store_name))
                warehouse, _ = Warehouse.objects.get_or_create(store=store, name="Kho mặc định")
                balance = InventoryBalance.objects.create(
                    warehouse=warehouse, variant=variant, on_hand=quantity
                )
                StockMovement.objects.create(
                    balance=balance,
                    delta=quantity,
                    on_hand_after=quantity,
                    kind="INITIAL",
                    reference=f"master_dataset:{r['id']}",
                )
                counts["initial_stock"] += quantity
    counts["products_after"] = Product.objects.filter(source_namespace="master_dataset").count()
    counts["variants_after"] = ProductVariant.objects.filter(
        product__source_namespace="master_dataset"
    ).count()
    counts["source_stock"] = sum(r["total_stock"] for r in rows)
    counts["dry_run"] = dry_run
    if review:
        from .quality import review_master_catalog

        counts["catalog_review"] = review_master_catalog(changed_source_ids, dry_run=dry_run)
    if dry_run:
        transaction.set_rollback(True)
    return counts
