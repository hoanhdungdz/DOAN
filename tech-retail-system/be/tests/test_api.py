import hashlib
import re
from datetime import timedelta
from django.test import TestCase, override_settings
from django.utils import timezone
from django.core.cache import cache
from django.core import mail
from rest_framework.test import APIClient
from apps.accounts.models import User, ResetChallenge
from apps.orders.models import Order
from apps.orders.services import create_order, transition_order
from apps.payments.services import record_payment
from .factories import scenario, checkout, assign


class APITests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.s = scenario()

    def setUp(self):
        cache.clear()
        self.client = APIClient()

    def as_user(self, user):
        self.client.force_authenticate(user=user)

    def order(self, user=None, **kw):
        return create_order(
            checkout(self.s, **kw), user or self.s["customer"], "api", str(Order.objects.count())
        )

    def test_public_catalog_and_decimal_contract(self):
        response = self.client.get("/api/v1/products/")
        self.assertEqual(response.status_code, 200)
        row = response.json()["results"][0]
        self.assertNotIn("source_snapshot", row)
        self.assertEqual(row["variants"][0]["price"], "1234000.00")

    def test_catalog_filters(self):
        self.assertEqual(self.client.get("/api/v1/variants/?price_max=100").json()["count"], 0)
        self.assertEqual(self.client.get("/api/v1/products/?spec=16GB").json()["count"], 1)
        self.assertEqual(
            self.client.get("/api/v1/variants/?in_stock=true&store=" + str(self.s["b"].pk)).json()[
                "count"
            ],
            0,
        )
        self.assertEqual(self.client.get("/api/v1/variants/?price_min=NaN").status_code, 400)

    def test_disabled_category_hidden(self):
        c = self.s["p"].category
        c.is_active = False
        c.save()
        self.assertEqual(self.client.get("/api/v1/products/").json()["count"], 0)
        self.assertEqual(self.client.get("/api/v1/variants/").json()["count"], 0)

    def test_internal_query_cannot_expose_inactive_variant(self):
        v = self.s["v"]
        v.is_active = False
        v.save()
        for endpoint in ("products", "variants"):
            self.assertEqual(
                self.client.get(f"/api/v1/{endpoint}/?internal=true").json()["count"], 0
            )

    def test_numeric_specs_require_matching_unit(self):
        from apps.products.models import SpecificationDefinition, ProductSpecification

        definition = SpecificationDefinition.objects.create(name="Test memory")
        ProductSpecification.objects.create(
            product=self.s["p"],
            definition=definition,
            value="512MB",
            numeric_value="512",
            unit="MB",
        )
        base = f"/api/v1/products/?spec_definition={definition.pk}&spec_min=16"
        self.assertEqual(self.client.get(base).status_code, 400)
        self.assertEqual(self.client.get(base + "&spec_unit=GB").json()["count"], 0)
        self.assertEqual(self.client.get(base + "&spec_unit=MB").json()["count"], 1)

    def test_empty_role_assignment_does_not_grant_inventory_permission(self):
        assign(self.s["other"], self.s["a"])
        self.as_user(self.s["other"])
        self.assertEqual(self.client.get("/api/v1/inventory/").status_code, 403)

    def test_destination_manager_can_read_related_transfer_audit(self):
        from apps.inventory.models import StockTransfer, StockTransferItem
        from apps.inventory.services import transition_transfer

        transfer = StockTransfer.objects.create(
            source=self.s["wa"], destination=self.s["wb"], reason="Test", created_by=self.s["admin"]
        )
        StockTransferItem.objects.create(transfer=transfer, variant=self.s["v"], quantity=1)
        for action in ("approve", "dispatch", "receive"):
            transition_transfer(transfer.pk, action, self.s["admin"])
        assign(self.s["other"], self.s["b"], "view_audit")
        self.as_user(self.s["other"])
        self.assertEqual(self.client.get("/api/v1/audit-logs/").json()["count"], 3)

    def test_product_price_filters_match_same_variant_without_duplicates(self):
        from apps.products.models import ProductVariant

        ProductVariant.objects.create(
            product=self.s["p"], sku="SECOND-TEST", price="3000000", condition="Test"
        )
        self.assertEqual(self.client.get("/api/v1/products/?sort=price").json()["count"], 1)
        self.assertEqual(
            self.client.get("/api/v1/products/?price_min=2000000&price_max=2500000").json()[
                "count"
            ],
            0,
        )

    def test_invalid_id_filters_are_structured_errors(self):
        r = self.client.get("/api/v1/products/?category=invalid")
        self.assertEqual(r.status_code, 400)
        self.assertEqual(r.json()["code"], "INVALID_FILTER")

    def test_iphone_search_excludes_watch_compatibility_specs(self):
        from apps.products.models import Product, ProductVariant

        p = self.s["p"]
        p.name = "iPhone 16 Pro"
        p.save()
        watch = Product.objects.create(
            name="Apple Watch Series",
            slug="test-watch",
            category=p.category,
            brand=p.brand,
            source_id="TEST-WATCH",
            raw_specs="Tương thích: iPhone 8 trở lên",
        )
        ProductVariant.objects.create(
            product=watch, sku="WATCH-TEST", price="1000000", condition="Test"
        )
        for endpoint in ("products", "variants"):
            result = self.client.get(f"/api/v1/{endpoint}/?search=iphone").json()
            self.assertEqual(result["count"], 1)
        self.assertEqual(self.client.get("/api/v1/products/?spec=iPhone").json()["count"], 1)

    def test_customer_cannot_edit_catalog(self):
        self.as_user(self.s["customer"])
        r = self.client.patch(f"/api/v1/variants/{self.s['v'].pk}/", {"price": "1"}, format="json")
        self.assertEqual(r.status_code, 403)

    def test_price_change_audit_keeps_before_after(self):
        from common.models import AuditLog

        self.as_user(self.s["admin"])
        r = self.client.patch(
            f"/api/v1/variants/{self.s['v'].pk}/", {"price": "1999000.00"}, format="json"
        )
        self.assertEqual(r.status_code, 200)
        changes = AuditLog.objects.get(action="catalog.update").changes
        self.assertEqual(changes["before"]["price"], "1234000.00")
        self.assertEqual(changes["after"]["price"], "1999000.00")

    def test_checkout_server_price_and_public_status_injection(self):
        self.as_user(self.s["customer"])
        payload = checkout(self.s)
        payload.update(grand_total="1", status="COMPLETED", payment_status="PAID")
        r = self.client.post("/api/v1/orders/", payload, format="json", HTTP_IDEMPOTENCY_KEY="key")
        self.assertEqual(r.status_code, 201)
        self.assertEqual(r.json()["grand_total"], "1234000.00")
        self.assertEqual(r.json()["payment_status"], "UNPAID")
        self.assertEqual(r.json()["status"], "PENDING")

    def test_order_patch_forbidden(self):
        o = self.order()
        self.as_user(self.s["admin"])
        self.assertEqual(
            self.client.patch(
                f"/api/v1/orders/{o.pk}/", {"status": "COMPLETED"}, format="json"
            ).status_code,
            405,
        )

    def test_customer_owned_queryset_and_hidden_detail(self):
        self.order()
        other = self.order(self.s["other"])
        self.as_user(self.s["customer"])
        self.assertEqual(self.client.get("/api/v1/orders/").json()["count"], 1)
        self.assertEqual(self.client.get(f"/api/v1/orders/{other.pk}/").status_code, 404)

    def test_staff_other_branch_cannot_see_order_or_customer(self):
        self.order()
        assign(self.s["other"], self.s["b"], "manage_sales", "manage_people")
        self.as_user(self.s["other"])
        self.assertEqual(self.client.get("/api/v1/orders/").json()["count"], 0)
        self.assertEqual(self.client.get("/api/v1/customers/").json()["count"], 0)

    def test_customer_cannot_read_internal_balances(self):
        self.as_user(self.s["customer"])
        self.assertEqual(self.client.get("/api/v1/inventory/").status_code, 403)

    def test_staff_inventory_scope_and_no_patch(self):
        assign(self.s["other"], self.s["b"], "manage_stock")
        self.as_user(self.s["other"])
        self.assertEqual(self.client.get("/api/v1/inventory/").json()["count"], 0)
        self.as_user(self.s["admin"])
        self.assertEqual(
            self.client.patch(
                f"/api/v1/inventory/{self.s['balance'].pk}/", {"on_hand": 100}
            ).status_code,
            405,
        )

    def test_staff_cannot_escalate(self):
        assign(self.s["other"], self.s["a"], "manage_people")
        self.as_user(self.s["other"])
        self.assertEqual(
            self.client.post(
                "/api/v1/assignments/",
                {"user": self.s["other"].pk, "store": self.s["b"].pk, "group": 1},
                format="json",
            ).status_code,
            403,
        )
        self.assertEqual(self.client.get("/api/v1/users/").status_code, 403)

    def test_cart_replacement_merge_and_remove(self):
        self.as_user(self.s["customer"])
        body = {"items": [{"variant": self.s["v"].pk, "quantity": 2}]}
        self.assertEqual(self.client.put("/api/v1/carts/", body, format="json").status_code, 200)
        r = self.client.post("/api/v1/carts/", body, format="json")
        self.assertEqual(r.json()["items"][0]["quantity"], 4)
        r = self.client.delete("/api/v1/carts/?variant=" + str(self.s["v"].pk))
        self.assertEqual(r.json()["items"], [])

    def test_guest_cart_not_persisted_server(self):
        self.assertEqual(self.client.get("/api/v1/carts/").status_code, 403)

    def test_cart_merge_revalidates_stock_without_reserving(self):
        self.as_user(self.s["customer"])
        r = self.client.post(
            "/api/v1/carts/",
            {"items": [{"variant": self.s["v"].pk, "quantity": 11}]},
            format="json",
        )
        self.assertEqual(r.status_code, 200)
        self.assertTrue(r.json()["warnings"])
        self.s["balance"].refresh_from_db()
        self.assertEqual(self.s["balance"].reserved, 0)

    def test_merge_skips_discontinued_variant_with_explicit_warning(self):
        self.s["v"].is_active = False
        self.s["v"].save()
        self.as_user(self.s["customer"])
        r = self.client.post(
            "/api/v1/carts/", {"items": [{"variant": self.s["v"].pk, "quantity": 1}]}, format="json"
        )
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["items"], [])
        self.assertTrue(r.json()["warnings"])

    def test_cart_invalid_rolls_back(self):
        self.as_user(self.s["customer"])
        r = self.client.put(
            "/api/v1/carts/",
            {
                "items": [
                    {"variant": self.s["v"].pk, "quantity": 2},
                    {"variant": 999999, "quantity": 1},
                ]
            },
            format="json",
        )
        self.assertEqual(r.status_code, 400)
        self.assertEqual(self.client.get("/api/v1/carts/").json()["items"], [])

    def test_stock_document_api_create_post_immutable(self):
        self.as_user(self.s["admin"])
        r = self.client.post(
            "/api/v1/stock-documents/",
            {
                "warehouse": self.s["wa"].pk,
                "kind": "IN",
                "reason": "Test",
                "items": [{"variant": self.s["v"].pk, "quantity": 2}],
            },
            format="json",
        )
        self.assertEqual(r.status_code, 201)
        pk = r.json()["id"]
        self.assertEqual(self.client.post(f"/api/v1/stock-documents/{pk}/post/").status_code, 200)
        self.assertEqual(
            self.client.patch(
                f"/api/v1/stock-documents/{pk}/", {"reason": "Changed"}, format="json"
            ).status_code,
            409,
        )

    def test_document_creation_cross_branch_denied(self):
        assign(self.s["other"], self.s["b"], "manage_stock")
        self.as_user(self.s["other"])
        r = self.client.post(
            "/api/v1/stock-documents/",
            {
                "warehouse": self.s["wa"].pk,
                "kind": "IN",
                "reason": "Test",
                "items": [{"variant": self.s["v"].pk, "quantity": 2}],
            },
            format="json",
        )
        self.assertEqual(r.status_code, 403)

    def test_transfer_api_create_and_scope(self):
        self.as_user(self.s["admin"])
        r = self.client.post(
            "/api/v1/stock-transfers/",
            {
                "source": self.s["wa"].pk,
                "destination": self.s["wb"].pk,
                "reason": "Test",
                "items": [{"variant": self.s["v"].pk, "quantity": 2}],
            },
            format="json",
        )
        self.assertEqual(r.status_code, 201)
        pk = r.json()["id"]
        self.assertEqual(
            self.client.post(f"/api/v1/stock-transfers/{pk}/approve/").status_code, 200
        )
        self.assertEqual(
            self.client.post(f"/api/v1/stock-transfers/{pk}/dispatch/").status_code, 200
        )
        mismatch = self.client.post(
            f"/api/v1/stock-transfers/{pk}/receive/",
            {"items": [{"variant": self.s["v"].pk, "quantity": 1}]},
            format="json",
        )
        self.assertEqual(mismatch.status_code, 409)
        self.assertEqual(
            self.client.post(f"/api/v1/stock-transfers/{pk}/receive/").status_code, 200
        )

    def test_payment_api_customer_denied(self):
        o = self.order()
        self.as_user(self.s["customer"])
        r = self.client.post(
            "/api/v1/payments/",
            {"order": o.pk, "kind": "CAPTURE"},
            format="json",
            HTTP_IDEMPOTENCY_KEY="key",
        )
        self.assertEqual(r.status_code, 403)

    def test_payment_api_staff_capture(self):
        o = self.order()
        self.as_user(self.s["admin"])
        r = self.client.post(
            "/api/v1/payments/",
            {"order": o.pk, "kind": "CAPTURE"},
            format="json",
            HTTP_IDEMPOTENCY_KEY="key",
        )
        self.assertEqual(r.status_code, 201)
        self.assertEqual(r.json()["amount"], "1234000.00")

    def test_report_empty_and_branch_export_denied(self):
        assign(self.s["other"], self.s["a"], "view_reports")
        self.as_user(self.s["other"])
        r = self.client.get("/api/v1/reports/summary/")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["sales_net"], "0")
        self.assertEqual(
            self.client.get("/api/v1/reports/export/?store=" + str(self.s["b"].pk)).status_code, 403
        )

    def test_reports_completed_paid_only_and_timezone(self):
        o = self.order()
        self.as_user(self.s["admin"])
        self.assertEqual(self.client.get("/api/v1/reports/summary/").json()["completed_orders"], 0)
        for a in ["confirm", "pack", "ship"]:
            transition_order(o.pk, a, self.s["admin"])
        record_payment(o.pk, self.s["admin"], "CAPTURE", "key")
        transition_order(o.pk, "complete", self.s["admin"])
        # 17:30 UTC on Oct 12 is Oct 13 in Vietnam.
        instant = timezone.datetime(
            2026, 10, 12, 17, 30, tzinfo=__import__("datetime").timezone.utc
        )
        Order.objects.filter(pk=o.pk).update(completed_at=instant)
        r = self.client.get("/api/v1/reports/summary/?start=2026-10-13&end=2026-10-13").json()
        self.assertEqual(r["completed_orders"], 1)
        self.assertEqual(r["daily"][0]["day"], "2026-10-13")
        for key in ("bestsellers", "by_store", "by_channel"):
            self.assertIsInstance(r[key][0]["revenue"], str)
        self.assertEqual(r["monthly"][0]["month"], "2026-10")
        r = self.client.get("/api/v1/reports/summary/?start=2026-10-12&end=2026-10-12").json()
        self.assertEqual(r["completed_orders"], 0)

    def test_invoice_read_has_no_side_effect(self):
        o = self.order()
        for a in ["confirm", "pack", "ship"]:
            transition_order(o.pk, a, self.s["admin"])
        record_payment(o.pk, self.s["admin"], "CAPTURE", "key")
        transition_order(o.pk, "complete", self.s["admin"])
        self.as_user(self.s["customer"])
        self.client.get("/api/v1/invoices/")
        self.client.get("/api/v1/invoices/")
        self.assertEqual(o.transactions.count(), 1)
        self.s["balance"].refresh_from_db()
        self.assertEqual(self.s["balance"].on_hand, 9)

    def test_features_and_disabled_ai(self):
        self.assertEqual(self.client.get("/api/v1/features/").json()["gemini"], False)
        r = self.client.post("/api/v1/ai/chat/", {"question": "Laptop phù hợp?"}, format="json")
        self.assertEqual(r.status_code, 503)
        self.assertEqual(r.json()["code"], "AI_NOT_CONFIGURED")

    def test_retrieval_is_database_backed(self):
        r = self.client.get("/api/v1/ai/retrieval/?spec=16GB").json()["results"]
        self.assertEqual(r[0]["id"], self.s["v"].pk)
        self.assertEqual(r[0]["stock"][0]["available"], 10)

    def test_audit_excludes_tokens_and_pii(self):
        from common.models import AuditLog

        self.order()
        rows = list(AuditLog.objects.values_list("changes", flat=True))
        self.assertTrue(rows)
        self.assertNotIn("password", str(rows))
        self.assertNotIn("0901234567", str(rows))


class SessionSecurityTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user("login@test.invalid", "Test-password-2026!")

    def setUp(self):
        cache.clear()
        self.client = APIClient(enforce_csrf_checks=True)

    def csrf(self):
        token = self.client.get("/api/v1/auth/csrf/").json()["csrfToken"]
        self.client.credentials(HTTP_X_CSRFTOKEN=token)

    def test_login_requires_csrf(self):
        r = self.client.post(
            "/api/v1/auth/login/",
            {"email": self.user.email, "password": "Test-password-2026!"},
            format="json",
        )
        self.assertEqual(r.status_code, 403)

    def test_anonymous_checkout_requires_csrf(self):
        self.assertEqual(self.client.post("/api/v1/orders/", {}, format="json").status_code, 403)

    def test_login_cookie_logout_session(self):
        self.csrf()
        r = self.client.post(
            "/api/v1/auth/login/",
            {"email": self.user.email, "password": "Test-password-2026!"},
            format="json",
        )
        self.assertEqual(r.status_code, 200)
        self.assertTrue(r.cookies["sessionid"]["httponly"])
        self.assertEqual(self.client.get("/api/v1/auth/me/").json()["user"]["id"], self.user.pk)
        self.client.credentials(HTTP_X_CSRFTOKEN=r.json()["csrfToken"])
        self.assertEqual(
            self.client.post("/api/v1/auth/logout/", {}, format="json").status_code, 200
        )
        self.assertIsNone(self.client.get("/api/v1/auth/me/").json()["user"])

    def test_locked_user_existing_session_blocked(self):
        self.client.force_login(self.user)
        User.objects.filter(pk=self.user.pk).update(is_active=False)
        self.assertIsNone(self.client.get("/api/v1/auth/me/").json()["user"])

    def test_registration_email_normalization_no_escalation(self):
        self.csrf()
        r = self.client.post(
            "/api/v1/auth/register/",
            {
                "email": " New@TEST.invalid ",
                "password": "Another-test-password!",
                "full_name": "Test",
                "is_superuser": True,
                "roles": ["Admin"],
            },
            format="json",
        )
        self.assertEqual(r.status_code, 200)
        user = User.objects.get(email="new@test.invalid")
        self.assertFalse(user.is_superuser)
        self.assertFalse(user.assignments.exists())

    @override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
    def test_password_reset_no_enumeration_and_single_use(self):
        self.csrf()
        with self.captureOnCommitCallbacks(execute=True):
            r = self.client.post(
                "/api/v1/auth/forgot-password/", {"email": self.user.email}, format="json"
            )
        r2 = self.client.post(
            "/api/v1/auth/forgot-password/", {"email": "unknown@test.invalid"}, format="json"
        )
        self.assertEqual(r.json(), r2.json())
        self.assertNotIn("token", r.json())
        token = re.search(r"token=([\w-]+)", mail.outbox[0].body)[1]
        body = {"token": token, "password": "New-safe-password!"}
        self.assertEqual(
            self.client.post("/api/v1/auth/reset-password/", body, format="json").status_code, 200
        )
        self.assertEqual(
            self.client.post("/api/v1/auth/reset-password/", body, format="json").status_code, 400
        )

    def test_reset_expired(self):
        self.csrf()
        ResetChallenge.objects.create(
            user=self.user,
            token_hash=hashlib.sha256(b"expired").hexdigest(),
            expires_at=timezone.now() - timedelta(seconds=1),
        )
        self.assertEqual(
            self.client.post(
                "/api/v1/auth/reset-password/",
                {"token": "expired", "password": "New-safe-password!"},
                format="json",
            ).status_code,
            400,
        )
