"""Reviewed source metadata corrections; never merge identities or change stock."""

import json
import re
from decimal import Decimal
from django.conf import settings
from django.db import transaction
from common.audit import audit
from .models import Category, Product


def contradicts_used_title(name, condition):
    return bool(re.search(r"\bcũ\b", name, re.IGNORECASE)) and condition.casefold().startswith(
        "mới"
    )


def matches_source(product, expected):
    return all(product.source_snapshot.get(key) == value for key, value in expected.items())


@transaction.atomic
def review_master_catalog(source_ids=None, dry_run=True):
    plan = json.loads((settings.BASE_DIR / "data/catalog_corrections.json").read_text("utf-8"))
    result = {"dry_run": dry_run, "changes": [], "conflicts": []}
    for rule in plan:
        if source_ids is not None and rule["source_id"] not in source_ids:
            continue
        product = (
            Product.objects.select_for_update()
            .select_related("category")
            .filter(source_namespace="master_dataset", source_id=rule["source_id"])
            .first()
        )
        if product is None:
            continue
        if not matches_source(product, rule["expected"]):
            result["conflicts"].append({"source_id": rule["source_id"], "reason": "SOURCE_CHANGED"})
            continue
        obj = product
        before, after = {}, {}
        if rule["kind"] == "category":
            if product.category.source_key == rule["value"]:
                continue
            if product.category.source_key != rule["expected"]["category"]:
                result["conflicts"].append(
                    {"source_id": rule["source_id"], "reason": "CATEGORY_EDITED"}
                )
                continue
            category, _ = Category.objects.get_or_create(
                source_key=rule["value"], defaults={"name": rule["label"]}
            )
            before = {"category": product.category_id}
            product.category = category
            after = {"category": category.pk}
            product.save(update_fields=["category", "updated_at"])
        elif rule["kind"] == "condition":
            obj = product.variants.select_for_update().filter(sku=rule["expected"]["sku"]).first()
            if obj is None or obj.condition == rule["value"]:
                continue
            if obj.condition != rule["expected"]["condition"]:
                result["conflicts"].append(
                    {"source_id": rule["source_id"], "reason": "CONDITION_EDITED"}
                )
                continue
            before, after = {"condition": obj.condition}, {"condition": rule["value"]}
            obj.condition = rule["value"]
            obj.save(update_fields=["condition", "updated_at"])
        elif rule["kind"] == "duplicate":
            if not product.is_active:
                continue
            canonical = Product.objects.filter(
                source_namespace="master_dataset", source_id=rule["canonical"], is_active=True
            ).first()
            variants = list(product.variants.select_for_update())
            v = variants[0] if len(variants) == 1 else None
            canonical_variants = list(canonical.variants.all()) if canonical else []
            cv = canonical_variants[0] if len(canonical_variants) == 1 else None
            if (
                canonical is None
                or not matches_source(canonical, rule["canonical_expected"])
                or canonical.name != rule["canonical_expected"]["name"]
                or canonical.category_id != product.category_id
                or canonical.brand_id != product.brand_id
                or product.name != rule["expected"]["name"]
                or not v
                or not cv
                or cv.price != v.price
                or cv.condition != v.condition
                or cv.attributes
                or v.sku != rule["expected"]["sku"]
                or v.condition != rule["expected"]["condition"]
                or v.price != Decimal(str(product.source_snapshot["price"]))
                or v.attributes
            ):
                result["conflicts"].append(
                    {"source_id": rule["source_id"], "reason": "DUPLICATE_REQUIRES_REVIEW"}
                )
                continue
            before, after = {"is_active": True}, {"is_active": False}
            product.is_active = False
            product.save(update_fields=["is_active", "updated_at"])
        audit(
            None,
            "catalog.source_review",
            obj,
            before=before,
            after=after,
            source_id=rule["source_id"],
            canonical=rule.get("canonical"),
            reason=rule["reason"],
        )
        result["changes"].append(
            {
                "source_id": rule["source_id"],
                "kind": rule["kind"],
                "before": before,
                "after": after,
                "canonical": rule.get("canonical"),
            }
        )
    if dry_run:
        transaction.set_rollback(True)
    return result
