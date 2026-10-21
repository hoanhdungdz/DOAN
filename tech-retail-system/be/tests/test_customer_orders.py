from datetime import timedelta

from django.contrib.auth.models import AnonymousUser
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from apps.orders.models import Order, OTPChallenge
from apps.orders.services import create_order
from .factories import scenario, checkout, assign


class PersonalOrderTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.s = scenario(quantity=20)
        cls.owned = create_order(checkout(cls.s), cls.s["customer"], "owned", "one")
        cls.other = create_order(checkout(cls.s), cls.s["other"], "other", "two")
        cls.admin_owned = create_order(checkout(cls.s), cls.s["admin"], "admin", "three")
        # Historical guest orders must never be claimed using a matching phone.
        cls.guest = create_order(checkout(cls.s), AnonymousUser(), "legacy-guest", "four")

    def setUp(self):
        self.client = APIClient()

    def test_anonymous_cannot_list_read_or_create_orders(self):
        for path in [
            "my-orders/",
            f"my-orders/{self.owned.pk}/",
            "orders/",
            f"orders/{self.owned.pk}/",
        ]:
            self.assertEqual(self.client.get("/api/v1/" + path).status_code, 403)
        before = Order.objects.count()
        response = self.client.post(
            "/api/v1/orders/", checkout(self.s), format="json", HTTP_IDEMPOTENCY_KEY="anon-denied"
        )
        self.assertEqual(response.status_code, 403)
        self.assertEqual(Order.objects.count(), before)

    def test_customer_can_read_full_details_without_otp(self):
        self.client.force_authenticate(self.s["customer"])
        result = self.client.get(f"/api/v1/my-orders/{self.owned.pk}/")
        self.assertEqual(result.status_code, 200)
        self.assertEqual(result.json()["code"], self.owned.code)
        self.assertEqual(result.json()["phone"], self.owned.phone)
        self.assertEqual(result.json()["address"], self.owned.address)
        self.assertEqual(len(result.json()["items"]), 1)
        self.assertTrue(result.json()["history"])
        self.assertFalse(OTPChallenge.objects.exists())

    def test_personal_list_contains_only_owned_orders(self):
        self.client.force_authenticate(self.s["customer"])
        data = self.client.get(
            "/api/v1/my-orders/?internal=true&customer=" + str(self.other.customer_id)
        ).json()
        self.assertEqual(data["count"], 1)
        self.assertEqual([row["id"] for row in data["results"]], [self.owned.pk])

    def test_other_customer_and_guest_details_are_hidden(self):
        self.client.force_authenticate(self.s["customer"])
        for order in [self.other, self.admin_owned, self.guest]:
            self.assertEqual(self.client.get(f"/api/v1/my-orders/{order.pk}/").status_code, 404)

    def test_search_cannot_find_another_customers_order_code(self):
        self.client.force_authenticate(self.s["customer"])
        self.assertEqual(
            self.client.get("/api/v1/my-orders/?search=" + self.other.code).json()["count"], 0
        )

    def test_employee_branch_permissions_do_not_expand_personal_history(self):
        assign(self.s["other"], self.s["a"], "manage_sales")
        self.client.force_authenticate(self.s["other"])
        self.assertEqual(self.client.get("/api/v1/orders/").json()["count"], 4)
        data = self.client.get("/api/v1/my-orders/").json()
        self.assertEqual([row["id"] for row in data["results"]], [self.other.pk])
        self.assertEqual(self.client.get(f"/api/v1/my-orders/{self.owned.pk}/").status_code, 404)

    def test_admin_personal_history_still_means_only_their_own_orders(self):
        self.client.force_authenticate(self.s["admin"])
        self.assertEqual(self.client.get("/api/v1/orders/").json()["count"], 4)
        data = self.client.get("/api/v1/my-orders/").json()
        self.assertEqual([row["id"] for row in data["results"]], [self.admin_owned.pk])

    def test_authenticated_checkout_binds_the_session_account(self):
        self.client.force_authenticate(self.s["customer"])
        response = self.client.post(
            "/api/v1/orders/",
            checkout(self.s),
            format="json",
            HTTP_IDEMPOTENCY_KEY="new-personal-order",
        )
        self.assertEqual(response.status_code, 201)
        created = Order.objects.get(pk=response.json()["id"])
        self.assertEqual(created.customer.user_id, self.s["customer"].pk)
        self.assertEqual(self.client.get(f"/api/v1/my-orders/{created.pk}/").status_code, 200)

    def test_account_cannot_be_overridden_when_creating_an_online_order(self):
        self.client.force_authenticate(self.s["customer"])
        response = self.client.post(
            "/api/v1/orders/",
            checkout(self.s, customer=self.other.customer_id),
            format="json",
            HTTP_IDEMPOTENCY_KEY="cannot-impersonate",
        )
        self.assertEqual(response.status_code, 400)

    def test_owner_can_cancel_pending_order(self):
        self.client.force_authenticate(self.s["customer"])
        response = self.client.post(
            f"/api/v1/my-orders/{self.owned.pk}/cancel/",
            {"reason": "Khách đổi kế hoạch"},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "CANCELLED")

    def test_cancel_and_write_cannot_target_someone_elses_order(self):
        self.client.force_authenticate(self.s["customer"])
        response = self.client.post(
            f"/api/v1/my-orders/{self.other.pk}/cancel/", {"reason": "Not mine"}, format="json"
        )
        self.assertEqual(response.status_code, 404)
        self.other.refresh_from_db()
        self.assertEqual(self.other.status, "PENDING")
        self.assertEqual(
            self.client.patch(
                f"/api/v1/my-orders/{self.owned.pk}/", {"status": "COMPLETED"}, format="json"
            ).status_code,
            405,
        )

    def test_retired_otp_endpoints_cannot_create_or_use_a_legacy_grant(self):
        session = self.client.session
        session["order_lookup"] = {
            "order": self.other.pk,
            "expires": (timezone.now() + timedelta(minutes=10)).timestamp(),
        }
        session.save()
        for action, method in [("request", "post"), ("verify", "post"), ("result", "get")]:
            response = getattr(self.client, method)(f"/api/v1/order-lookup/{action}/")
            self.assertEqual(response.status_code, 404)
        self.assertEqual(self.client.get(f"/api/v1/my-orders/{self.other.pk}/").status_code, 403)
        self.assertFalse(OTPChallenge.objects.exists())
