from django.test import TestCase
from rest_framework.test import APIClient
from apps.accounts.models import User
from apps.stores.models import Store, Warehouse
from apps.inventory.models import StockTransfer, StockTransferItem
from apps.products.models import ProductVariant
from .factories import scenario, assign


class TransferLookupTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.s = scenario()
        cls.s["a"].name = "Cầu Giấy"
        cls.s["a"].save()
        cls.s["b"].name = "Thanh Xuân"
        cls.s["b"].save()
        cls.s["wa"].name = "Kho nguồn Alpha"
        cls.s["wa"].save()
        cls.s["wb"].name = "Kho đích Beta"
        cls.s["wb"].save()
        cls.transfer = StockTransfer.objects.create(
            source=cls.s["wa"],
            destination=cls.s["wb"],
            reason="Bổ sung hàng",
            created_by=cls.s["admin"],
        )
        StockTransferItem.objects.create(transfer=cls.transfer, variant=cls.s["v"], quantity=2)
        extra = ProductVariant.objects.create(
            product=cls.s["p"], sku="SECOND-SKU", price=123, condition="Test"
        )
        StockTransferItem.objects.create(transfer=cls.transfer, variant=extra, quantity=1)

    def setUp(self):
        self.client = APIClient()
        self.client.force_authenticate(self.s["admin"])

    def test_search_matches_warehouse_store_product_and_sku_without_duplicates(self):
        for text in [
            "Alpha",
            "Beta",
            "Cầu Giấy",
            "Thanh Xuân",
            "Test product",
            "SECOND-SKU",
            "Bổ sung",
        ]:
            result = self.client.get("/api/v1/stock-transfers/", {"search": text})
            self.assertEqual(result.status_code, 200, result.content)
            self.assertEqual(result.json()["count"], 1)
            self.assertEqual(result.json()["results"][0]["id"], self.transfer.pk)
        self.s["balance"].refresh_from_db()
        self.assertEqual(self.s["balance"].on_hand, 10)

    def test_labels_include_branch_and_warehouse_and_item_names(self):
        row = self.client.get(f"/api/v1/stock-transfers/{self.transfer.pk}/").json()
        self.assertEqual(row["source_label"], "Cầu Giấy — Kho nguồn Alpha")
        self.assertEqual(row["destination_label"], "Thanh Xuân — Kho đích Beta")
        self.assertEqual(row["items"][0]["name"], "Test product")

    def test_search_never_broadens_branch_permissions(self):
        limited = User.objects.create_user("lookup-staff@test.invalid", "Test-password-2026!")
        assign(limited, self.s["a"], "manage_stock")
        other = Store.objects.create(name="Other branch")
        warehouse = Warehouse.objects.create(name="Other Alpha", store=other)
        destination = Warehouse.objects.create(name="Other destination", store=other)
        private = StockTransfer.objects.create(
            source=warehouse,
            destination=destination,
            reason="Alpha private",
            created_by=self.s["admin"],
        )
        StockTransferItem.objects.create(transfer=private, variant=self.s["v"], quantity=1)
        self.client.force_authenticate(limited)
        for text in ["Alpha", "Test product"]:
            rows = self.client.get("/api/v1/stock-transfers/", {"search": text}).json()["results"]
            self.assertEqual([row["id"] for row in rows], [self.transfer.pk])
