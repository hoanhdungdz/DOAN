import json
from decimal import Decimal
from django.conf import settings
from django.test import TestCase
from django.contrib.auth.models import AnonymousUser
from rest_framework.test import APIClient
from apps.products.importer import import_dataset
from apps.products.quality import review_master_catalog
from apps.products.api import ProductSerializer, VariantSerializer
from apps.products.models import Category, Product, ProductVariant
from apps.inventory.models import InventoryBalance, StockMovement
from apps.orders.services import create_order
from apps.orders.models import Order
from common.models import AuditLog
from common.errors import BusinessError


class CatalogQualityTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.path = settings.BASE_DIR / "data/final_master_dataset.json"
        import_dataset(cls.path, review=False)

    def product(self, source_id):
        return Product.objects.get(source_namespace="master_dataset", source_id=source_id)

    def test_dry_run_reports_metadata_changes_and_rolls_back_audits_and_category(self):
        before = list(Product.objects.order_by("id").values_list("id", "category_id", "is_active"))
        result = review_master_catalog()
        self.assertEqual(len(result["changes"]), 31)
        self.assertEqual(result["conflicts"], [])
        self.assertEqual(
            before,
            list(Product.objects.order_by("id").values_list("id", "category_id", "is_active")),
        )
        self.assertEqual(Category.objects.count(), 7)
        self.assertFalse(AuditLog.objects.exists())

    def test_review_preserves_all_source_records_stock_and_snapshots(self):
        balances = list(
            InventoryBalance.objects.order_by("id").values_list("id", "on_hand", "reserved")
        )
        movements = StockMovement.objects.count()
        result = review_master_catalog(dry_run=False)
        self.assertEqual(len(result["changes"]), 31)
        self.assertEqual(Product.objects.count(), 278)
        self.assertEqual(ProductVariant.objects.count(), 278)
        self.assertEqual(Product.objects.filter(is_active=True).count(), 264)
        self.assertEqual(
            Category.objects.get(source_key="Gia_dung_Smarthome")
            .product_set.filter(is_active=True)
            .count(),
            11,
        )
        self.assertEqual(
            Product.objects.filter(
                name__icontains="Mac mini", category__source_key="May_tinh_de_ban"
            ).count(),
            13,
        )
        self.assertEqual(ProductVariant.objects.filter(condition="Đã qua sử dụng").count(), 4)
        self.assertEqual(
            balances,
            list(InventoryBalance.objects.order_by("id").values_list("id", "on_hand", "reserved")),
        )
        self.assertEqual(StockMovement.objects.count(), movements)
        for row in json.loads(self.path.read_text("utf-8")):
            self.assertEqual(self.product(row["id"]).source_snapshot, row)
        # Same title/slug alone does not make the two differently priced Dell SKUs duplicates.
        self.assertTrue(self.product("PROD_0042").is_active)
        self.assertTrue(self.product("PROD_0043").is_active)

    def test_public_api_and_checkout_exclude_quarantined_duplicates(self):
        review_master_catalog(dry_run=False)
        client = APIClient()
        category = Category.objects.get(source_key="Gia_dung_Smarthome")
        result = client.get(f"/api/v1/products/?category={category.pk}&page_size=100").json()
        self.assertEqual(result["count"], 11)
        self.assertEqual(sum("Dreame L10s Ultra Gen 2" in r["name"] for r in result["results"]), 1)
        self.assertEqual(sum("Xiaomi Vacuum X20+" in r["name"] for r in result["results"]), 1)
        self.assertEqual(
            client.get("/api/v1/products/?condition=Đã qua sử dụng").json()["count"], 4
        )
        monitor = Category.objects.get(source_key="Man_hinh_PC")
        self.assertEqual(
            client.get(f"/api/v1/products/?category={monitor.pk}&search=Mac%20mini").json()[
                "count"
            ],
            0,
        )
        duplicate = self.product("PROD_0273")
        variant = duplicate.variants.get()
        self.assertEqual(client.get(f"/api/v1/variants/?search={variant.sku}").json()["count"], 0)
        balance = variant.balances.filter(on_hand__gt=0).first()
        with self.assertRaises(BusinessError):
            create_order(
                {
                    "warehouse": balance.warehouse_id,
                    "items": [{"variant": variant.pk, "quantity": 1}],
                    "recipient_name": "Quality test",
                    "phone": "0900000000",
                    "address": "Test",
                    "fulfillment": "DELIVERY",
                    "payment_method": "COD",
                },
                AnonymousUser(),
                "quality",
                "duplicate-checkout",
            )
        self.assertEqual(Order.objects.count(), 0)

    def test_reapply_and_reimport_are_idempotent(self):
        review_master_catalog(dry_run=False)
        count = AuditLog.objects.count()
        self.assertEqual(review_master_catalog(dry_run=False)["changes"], [])
        result = import_dataset(self.path)
        self.assertEqual(result["skip"], 278)
        self.assertEqual(result["catalog_review"]["changes"], [])
        self.assertEqual(AuditLog.objects.count(), count)
        self.assertEqual(Product.objects.filter(is_active=True).count(), 264)
        self.assertEqual(ProductVariant.objects.filter(condition="Đã qua sử dụng").count(), 4)

    def test_operational_edits_require_review_instead_of_being_overwritten(self):
        duplicate = self.product("PROD_0273")
        variant = duplicate.variants.get()
        variant.price += Decimal("1")
        variant.save()
        used = self.product("PROD_0072").variants.get()
        used.condition = "Cũ đẹp (Like New)"
        used.save()
        result = review_master_catalog(dry_run=False)
        self.assertEqual({r["source_id"] for r in result["conflicts"]}, {"PROD_0273", "PROD_0072"})
        duplicate.refresh_from_db()
        used.refresh_from_db()
        self.assertTrue(duplicate.is_active)
        self.assertEqual(used.condition, "Cũ đẹp (Like New)")

    def test_serializers_reject_used_name_with_new_condition(self):
        product = self.product("PROD_0072")
        variant = product.variants.get()
        serializer = VariantSerializer(
            variant, data={"condition": "Mới 100% (Chính hãng)"}, partial=True
        )
        self.assertFalse(serializer.is_valid())
        self.assertIn("condition", serializer.errors)
        serializer = ProductSerializer(product, data={"name": product.name}, partial=True)
        self.assertFalse(serializer.is_valid())
        review_master_catalog(dry_run=False)
        variant.refresh_from_db()
        self.assertTrue(
            VariantSerializer(variant, data={"price": "9000000.00"}, partial=True).is_valid()
        )
