from django.test import TestCase
from django.contrib.auth.models import AnonymousUser
from rest_framework.test import APIClient
from common.errors import BusinessError
from apps.customers.models import Customer
from apps.orders.models import Order
from apps.orders.services import create_order
from apps.payments.services import record_payment
from apps.products.models import ProductImage, ProductSpecification, SpecificationDefinition
from .factories import scenario, checkout, assign


class ManagementTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.s = scenario()

    def setUp(self):
        self.client = APIClient()
        self.client.force_authenticate(self.s["admin"])

    def test_pos_can_explicitly_select_existing_customer(self):
        online = create_order(checkout(self.s), self.s["customer"], "online", "key")
        assign(self.s["other"], self.s["a"], "manage_sales", "manage_payments")
        payload = checkout(
            self.s,
            channel="IN_STORE",
            payment_method="CASH",
            fulfillment="PICKUP",
            customer=online.customer_id,
        )
        pos = create_order(payload, self.s["other"], "pos", "key")
        self.assertEqual(pos.customer_id, online.customer_id)
        self.assertEqual(pos.seller_id, self.s["other"].pk)

    def test_pos_cannot_select_customer_from_unassigned_branch(self):
        foreign = Customer.objects.create(name="Foreign test")
        Order.objects.create(
            customer=foreign,
            warehouse=self.s["wb"],
            payment_method="COD",
            recipient_name="Test",
            phone="0901111111",
        )
        assign(self.s["other"], self.s["a"], "manage_sales")
        payload = checkout(
            self.s,
            channel="IN_STORE",
            payment_method="CASH",
            fulfillment="PICKUP",
            customer=foreign.pk,
        )
        with self.assertRaises(BusinessError):
            create_order(payload, self.s["other"], "pos", "key")
        self.assertEqual(Order.objects.count(), 1)

    def test_pos_draft_capture_must_go_through_finish(self):
        pos = create_order(
            checkout(self.s, channel="IN_STORE", payment_method="CASH", fulfillment="PICKUP"),
            self.s["admin"],
            "pos",
            "key",
        )
        with self.assertRaises(BusinessError):
            record_payment(pos.pk, self.s["admin"], "CAPTURE", "capture")
        self.assertFalse(pos.transactions.exists())

    def test_history_search_and_warehouse_scope_filters(self):
        self.assertEqual(self.client.get("/api/v1/movements/?search=NO_MATCH").json()["count"], 0)
        self.assertEqual(self.client.get("/api/v1/movements/?search=TEST-SKU").json()["count"], 1)
        assign(self.s["other"], self.s["a"], "manage_sales")
        self.client.force_authenticate(self.s["other"])
        rows = self.client.get("/api/v1/warehouses/?scope=sales").json()["results"]
        self.assertEqual([w["id"] for w in rows], [self.s["wa"].pk])

    def test_only_admin_can_remove_image_and_spec_metadata(self):
        image = ProductImage.objects.create(
            product=self.s["p"], url="https://example.invalid/image.png"
        )
        definition = SpecificationDefinition.objects.create(name="Test definition")
        spec = ProductSpecification.objects.create(
            product=self.s["p"], definition=definition, value="Text"
        )
        self.client.force_authenticate(self.s["customer"])
        self.assertEqual(self.client.delete(f"/api/v1/product-images/{image.pk}/").status_code, 403)
        self.client.force_authenticate(self.s["admin"])
        self.assertEqual(self.client.delete(f"/api/v1/product-images/{image.pk}/").status_code, 204)
        self.assertEqual(self.client.delete(f"/api/v1/specifications/{spec.pk}/").status_code, 204)
        self.assertEqual(
            self.client.delete(f"/api/v1/products/{self.s['p'].slug}/").status_code, 405
        )

    def test_admin_can_reactivate_inactive_catalog_without_public_bypass(self):
        v = self.s["v"]
        v.is_active = False
        v.save()
        self.client.force_authenticate(AnonymousUser())
        self.assertEqual(self.client.get("/api/v1/variants/?internal=true").json()["count"], 0)
        self.client.force_authenticate(self.s["admin"])
        r = self.client.patch(f"/api/v1/variants/{v.pk}/", {"is_active": True}, format="json")
        self.assertEqual(r.status_code, 200)
        self.assertTrue(r.json()["is_active"])
