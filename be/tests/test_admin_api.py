from django.test import TestCase
from django.core.cache import cache
from rest_framework.test import APIClient
from .factories import scenario


class AdminAPITests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.s = scenario()

    def setUp(self):
        cache.clear()
        self.client = APIClient()
        self.client.force_authenticate(self.s["admin"])

    def test_all_internal_list_endpoints(self):
        for endpoint in [
            "users",
            "roles",
            "permissions",
            "assignments",
            "employees",
            "customers",
            "products",
            "variants",
            "categories",
            "brands",
            "product-images",
            "specifications",
            "specification-definitions",
            "stores",
            "warehouses",
            "suppliers",
            "inventory",
            "movements",
            "reservations",
            "stock-documents",
            "stock-transfers",
            "orders",
            "payments",
            "invoices",
            "audit-logs",
        ]:
            with self.subTest(endpoint=endpoint):
                self.assertEqual(
                    self.client.get(f"/api/v1/{endpoint}/?internal=true").status_code, 200
                )

    def test_admin_creates_and_edits_business_master_data(self):
        def create(endpoint, body):
            r = self.client.post(f"/api/v1/{endpoint}/", body, format="json")
            self.assertEqual(r.status_code, 201, (endpoint, r.data))
            return r.json()

        category = create("categories", {"name": "API category", "source_key": "API_TEST"})
        brand = create("brands", {"name": "API brand"})
        product = create(
            "products",
            {
                "name": "API product",
                "slug": "api-product",
                "category": category["id"],
                "brand": brand["id"],
            },
        )
        variant = create(
            "variants",
            {
                "product": product["id"],
                "sku": "API-SKU",
                "price": "123.50",
                "condition": "Test",
                "warranty_months": 12,
            },
        )
        self.assertEqual(variant["price"], "123.50")
        create(
            "product-images",
            {"product": product["id"], "url": "https://example.invalid/product.png"},
        )
        definition = create("specification-definitions", {"name": "API RAM"})
        create(
            "specifications",
            {
                "product": product["id"],
                "definition": definition["id"],
                "value": "16GB",
                "numeric_value": "16",
                "unit": "GB",
            },
        )
        store = create("stores", {"name": "API store"})
        create("warehouses", {"store": store["id"], "name": "API warehouse"})
        create("suppliers", {"name": "API supplier"})
        user = create(
            "users",
            {
                "email": "api-staff@test.invalid",
                "full_name": "API staff",
                "password": "Api-staff-password!2026",
            },
        )
        self.assertNotIn("password", user)
        from common.models import AuditLog

        self.assertNotIn(
            "Api-staff-password!2026", str(list(AuditLog.objects.values_list("changes", flat=True)))
        )
        create("employees", {"user": user["id"], "code": "API-EMP"})
        role = create("roles", {"name": "API role", "permissions": []})
        assignment = create(
            "assignments", {"user": user["id"], "group": role["id"], "store": store["id"]}
        )
        r = self.client.patch(f"/api/v1/users/{user['id']}/", {"is_active": False}, format="json")
        self.assertEqual(r.status_code, 200)
        self.assertFalse(r.json()["is_active"])
        self.assertEqual(
            self.client.delete(f"/api/v1/assignments/{assignment['id']}/").status_code, 204
        )
