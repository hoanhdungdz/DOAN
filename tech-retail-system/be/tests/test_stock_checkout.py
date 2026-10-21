from django.core.cache import cache
from django.test import TestCase
from django.utils import timezone
from datetime import timedelta
from rest_framework.test import APIClient

from apps.inventory.models import InventoryBalance, StockMovement
from apps.orders.models import Order
from apps.orders.services import create_order
from .factories import scenario, checkout, assign


class StockCheckoutTests(TestCase):
    def setUp(self):
        cache.clear()
        self.s = scenario(quantity=3)
        self.client = APIClient()

    def test_availability_releases_only_expired_holds_and_does_not_place_an_order(self):
        order = create_order(
            checkout(self.s, items=[{"variant": self.s["v"].pk, "quantity": 3}]),
            self.s["other"],
            "expired",
            "one",
        )
        Order.objects.filter(pk=order.pk).update(expires_at=timezone.now() - timedelta(seconds=1))
        self.client.force_authenticate(self.s["customer"])
        response = self.client.post(
            "/api/v1/carts/availability/",
            {"items": [{"variant": self.s["v"].pk, "quantity": 1}]},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["items"][0]["details"]["stock"][0]["available"], 3)
        order.refresh_from_db()
        self.assertEqual(order.status, "CANCELLED")
        self.assertEqual(Order.objects.count(), 1)

    def test_availability_does_not_release_current_holds_and_requires_login(self):
        order = create_order(
            checkout(self.s, items=[{"variant": self.s["v"].pk, "quantity": 3}]),
            self.s["other"],
            "current",
            "one",
        )
        payload = {"items": [{"variant": self.s["v"].pk, "quantity": 1}]}
        self.assertEqual(
            self.client.post("/api/v1/carts/availability/", payload, format="json").status_code, 403
        )
        self.client.force_authenticate(self.s["customer"])
        response = self.client.post("/api/v1/carts/availability/", payload, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["items"][0]["details"]["stock"][0]["available"], 0)
        order.refresh_from_db()
        self.assertEqual(order.status, "PENDING")

    def test_checkout_at_empty_branch_explains_stock_and_rolls_back(self):
        self.client.force_authenticate(self.s["customer"])
        response = self.client.post(
            "/api/v1/orders/",
            checkout(self.s, warehouse=self.s["wb"].pk),
            format="json",
            HTTP_IDEMPOTENCY_KEY="empty-branch",
        )
        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.json()["code"], "INSUFFICIENT_STOCK")
        self.assertIn(self.s["b"].name, response.json()["message"])
        self.assertIn("chỉ còn 0", response.json()["message"])
        self.assertFalse(Order.objects.exists())
        self.s["balance"].refresh_from_db()
        self.assertEqual(self.s["balance"].on_hand, 3)
        self.assertEqual(self.s["balance"].reserved, 0)

    def test_inventory_exposes_branch_and_warehouse_names_with_scope(self):
        assign(self.s["other"], self.s["a"], "manage_stock")
        InventoryBalance.objects.create(variant=self.s["v"], warehouse=self.s["wb"], on_hand=8)
        self.client.force_authenticate(self.s["other"])
        rows = self.client.get("/api/v1/inventory/").json()["results"]
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["store_name"], self.s["a"].name)
        self.assertEqual(rows[0]["warehouse_name"], self.s["wa"].name)
        self.assertEqual(
            self.client.get(f"/api/v1/inventory/?store={self.s['b'].pk}").json()["count"], 0
        )

    def test_receipt_updates_on_hand_once_without_changing_reserved(self):
        create_order(checkout(self.s), self.s["customer"], "receipt-test", "one")
        self.client.force_authenticate(self.s["admin"])
        result = self.client.post(
            "/api/v1/stock-documents/",
            {
                "warehouse": self.s["wa"].pk,
                "kind": "IN",
                "reason": "Nhập bổ sung",
                "items": [{"variant": self.s["v"].pk, "quantity": 5}],
            },
            format="json",
        )
        self.assertEqual(result.status_code, 201)
        pk = result.json()["id"]
        for _ in range(2):
            self.assertEqual(
                self.client.post(
                    f"/api/v1/stock-documents/{pk}/post/", {}, format="json"
                ).status_code,
                200,
            )
        self.s["balance"].refresh_from_db()
        self.assertEqual(
            (self.s["balance"].on_hand, self.s["balance"].reserved, self.s["balance"].available),
            (8, 1, 7),
        )
        self.assertEqual(StockMovement.objects.filter(reference=f"DOC:{pk}").count(), 1)

    def test_receipt_cannot_cross_employee_scope_or_allow_customer_to_write(self):
        assign(self.s["other"], self.s["a"], "manage_stock")
        payload = {
            "warehouse": self.s["wb"].pk,
            "kind": "IN",
            "reason": "Nhập bổ sung",
            "items": [{"variant": self.s["v"].pk, "quantity": 5}],
        }
        for actor in [self.s["other"], self.s["customer"]]:
            self.client.force_authenticate(actor)
            self.assertEqual(
                self.client.post("/api/v1/stock-documents/", payload, format="json").status_code,
                403,
            )
