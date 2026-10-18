import json
import tempfile
from pathlib import Path
from decimal import Decimal
from django.test import TestCase
from django.conf import settings
from common.errors import BusinessError
from apps.products.importer import import_dataset, validate_dataset, parse_specs
from apps.products.models import Product, ProductVariant, Brand
from apps.inventory.models import InventoryBalance, StockMovement


class ImportTests(TestCase):
    path = settings.BASE_DIR / "data" / "final_master_dataset.json"

    def temp(self, rows):
        f = tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", suffix=".json", delete=False)
        json.dump(rows, f, ensure_ascii=False)
        f.close()
        self.addCleanup(Path(f.name).unlink)
        return f.name

    def test_validate_entire_source(self):
        rows = validate_dataset(self.path)
        self.assertEqual(len(rows), 278)
        self.assertEqual(sum(r["total_stock"] for r in rows), 2824)

    def test_full_dry_run_then_import_and_reimport_preserve_operational(self):
        r = import_dataset(self.path, True)
        self.assertEqual(r["create"], 278)
        self.assertFalse(Product.objects.exists())
        r = import_dataset(self.path)
        self.assertEqual((r["create"], r["initial_stock"]), (278, 2824))
        self.assertEqual(Product.objects.values("slug").distinct().count(), 278)
        self.assertEqual(Product.objects.filter(is_active=True).count(), 264)
        self.assertEqual(ProductVariant.objects.filter(condition="Đã qua sử dụng").count(), 4)
        self.assertEqual(Brand.objects.count(), 33)
        v = ProductVariant.objects.first()
        v.price = Decimal("900")
        v.save()
        b = InventoryBalance.objects.first()
        b.on_hand += 1
        b.save()
        StockMovement.objects.create(
            balance=b, delta=1, on_hand_after=b.on_hand, kind="TEST", reference="operational"
        )
        r = import_dataset(self.path)
        self.assertEqual(r["skip"], 278)
        v.refresh_from_db()
        b.refresh_from_db()
        self.assertEqual(v.price, Decimal("900"))
        self.assertEqual(
            b.on_hand,
            b.movements.aggregate(n=__import__("django.db.models", fromlist=["Sum"]).Sum("delta"))[
                "n"
            ],
        )
        self.assertEqual(ProductVariant.objects.count(), 278)

    def test_invalid_last_row_writes_nothing(self):
        rows = json.loads(self.path.read_text(encoding="utf-8"))
        rows[-1]["inventory"][next(iter(rows[-1]["inventory"]))] = -1
        with self.assertRaises(BusinessError):
            import_dataset(self.temp(rows))
        self.assertFalse(Product.objects.exists())

    def test_duplicate_sku_and_identity(self):
        rows = json.loads(self.path.read_text(encoding="utf-8"))[:2]
        rows[1]["sku"] = rows[0]["sku"]
        with self.assertRaises(BusinessError):
            validate_dataset(self.temp(rows))
        rows[1]["sku"] = "OTHER"
        rows[1]["id"] = rows[0]["id"]
        with self.assertRaises(BusinessError):
            validate_dataset(self.temp(rows))

    def test_conflict_rolls_back(self):
        rows = json.loads(self.path.read_text(encoding="utf-8"))[:1]
        path = self.temp(rows)
        import_dataset(path)
        rows[0]["id"] = "NEW-ID"
        with self.assertRaises(BusinessError):
            import_dataset(self.temp(rows))
        self.assertEqual(Product.objects.count(), 1)

    def test_extra_keys_preserved_and_brand_mapping(self):
        rows = json.loads(self.path.read_text(encoding="utf-8"))[:1]
        rows[0]["extra"] = "Keep"
        rows[0]["brand"] = "  Colorful  "
        import_dataset(self.temp(rows))
        p = Product.objects.get()
        self.assertEqual(p.source_snapshot["extra"], "Keep")
        self.assertEqual(p.brand.name, "Colorful")

    def test_specs_numeric_only_unambiguous(self):
        specs = list(parse_specs("RAM: 16GB | CPU: 8 lõi, 3 GHz | Màn hình: 15.6 inches"))
        self.assertEqual(specs[0][2], Decimal(16))
        self.assertIsNone(specs[1][2])
        self.assertEqual(specs[2][3], "inches")
