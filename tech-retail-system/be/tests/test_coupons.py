import hashlib
import hmac
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from datetime import timedelta
from decimal import Decimal
from urllib.parse import urlencode, parse_qs, urlsplit
from zoneinfo import ZoneInfo
from django.db import close_old_connections
from django.test import TestCase, TransactionTestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient
from common.errors import BusinessError
from apps.orders.models import Coupon, CouponRedemption, Order
from apps.orders.promotions import preview
from apps.orders.services import create_order, transition_order, invoice_for, expire_orders
from apps.payments.services import record_payment
from apps.payments.vnpay import create_attempt, receive_ipn
from apps.products.models import Category, Product, ProductVariant
from apps.inventory.models import InventoryBalance
from .factories import scenario, checkout


def coupon(code="TECH100K", **extra):
    now = timezone.now()
    return Coupon.objects.create(
        code=code,
        name="Test coupon",
        discount_type="FIXED",
        value=100000,
        min_subtotal=0,
        starts_at=now - timedelta(days=1),
        ends_at=now + timedelta(days=1),
        **extra,
    )


class CouponTests(TestCase):
    def setUp(self):
        self.s = scenario(quantity=50)
        self.coupon = coupon()

    def place(self, key="one", **extra):
        return create_order(
            checkout(self.s, coupon_code=self.coupon.code, **extra),
            self.s["customer"],
            "coupon-test",
            key,
        )

    def test_preview_server_prices_normalized_code_and_invalid_codes(self):
        client = APIClient()
        client.force_login(self.s["customer"])
        response = client.post(
            "/api/v1/checkout/promotions/",
            {
                "items": [{"variant": self.s["v"].pk, "quantity": 2, "price": 1}],
                "coupon_code": " tech100k ",
                "discount": 99999999,
            },
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        result = response.json()
        self.assertEqual(Decimal(result["grand_total"]), Decimal("2368000"))
        self.assertEqual(result["applied_coupon"]["code"], "TECH100K")
        self.assertEqual(CouponRedemption.objects.count(), 0)
        result = preview(checkout(self.s)["items"], self.s["customer"], "WRONG")
        self.assertTrue(result["coupon_error"])
        self.assertEqual(Decimal(result["discount_total"]), 0)

    def test_percentage_cap_whole_vnd_and_eligible_category_amount(self):
        self.coupon.discount_type, self.coupon.value = "PERCENT", Decimal("5.55")
        self.coupon.max_discount = 200000
        self.coupon.save()
        self.assertEqual(
            preview(checkout(self.s)["items"], self.s["customer"], "TECH100K")["discount_total"],
            "68487",
        )
        result = preview(
            [{"variant": self.s["v"].pk, "quantity": 10}], self.s["customer"], "TECH100K"
        )
        self.assertEqual(Decimal(result["discount_total"]), 200000)
        accessories = Category.objects.create(name="Accessories", source_key="accessories")
        self.coupon.categories.set([accessories])
        self.assertTrue(
            preview(checkout(self.s)["items"], self.s["customer"], "TECH100K")["coupon_error"]
        )
        p = Product.objects.create(
            name="Cable",
            slug="cable",
            category=accessories,
            brand=self.s["p"].brand,
            source_id="CABLE",
        )
        v = ProductVariant.objects.create(product=p, sku="CABLE", price=600000, condition="New")
        self.coupon.min_subtotal = 700000
        self.coupon.save()
        mixed = checkout(self.s)["items"] + [{"variant": v.pk, "quantity": 1}]
        self.assertTrue(preview(mixed, self.s["customer"], "TECH100K")["coupon_error"])
        self.coupon.min_subtotal = 500000
        self.coupon.save()
        self.assertEqual(preview(mixed, self.s["customer"], "TECH100K")["discount_total"], "33300")

    def test_order_snapshot_idempotency_and_invoice_are_stable_after_coupon_edit(self):
        order = self.place()
        self.assertEqual(order.subtotal, 1234000)
        self.assertEqual(order.discount_total, 100000)
        self.assertEqual(order.grand_total, 1134000)
        self.assertEqual(order.coupon_redemption.status, "RESERVED")
        self.coupon.value, self.coupon.is_active = 200000, False
        self.coupon.save()
        self.assertEqual(self.place().pk, order.pk)
        self.assertEqual(CouponRedemption.objects.count(), 1)
        order.refresh_from_db()
        self.assertEqual(order.coupon_snapshot["value"], "100000.00")
        self.assertEqual(invoice_for(order).snapshot["discount_total"], "100000.00")

    def test_cancel_and_expiration_return_held_usage(self):
        first = self.place()
        with self.assertRaises(BusinessError):
            self.place(key="two")
        transition_order(first.pk, "cancel", self.s["customer"], "Change plan")
        first.coupon_redemption.refresh_from_db()
        self.assertEqual(first.coupon_redemption.status, "RELEASED")
        second = self.place(key="three")
        Order.objects.filter(pk=second.pk).update(expires_at=timezone.now() - timedelta(seconds=1))
        self.assertTrue(
            preview(checkout(self.s)["items"], self.s["customer"], "TECH100K")["applied_coupon"]
        )
        expire_orders()
        second.coupon_redemption.refresh_from_db()
        self.assertEqual(second.coupon_redemption.status, "RELEASED")
        self.place(key="four")

    def test_capture_consumes_once_and_refund_does_not_restore_used_coupon(self):
        order = self.place()
        payment = record_payment(order.pk, self.s["admin"], "CAPTURE", "payment")
        self.assertEqual(payment.amount, 1134000)
        record_payment(order.pk, self.s["admin"], "CAPTURE", "payment")
        order.coupon_redemption.refresh_from_db()
        self.assertEqual(order.coupon_redemption.status, "USED")
        transition_order(order.pk, "cancel", self.s["admin"], "Refund")
        record_payment(order.pk, self.s["admin"], "REFUND", "refund", "receipt")
        self.assertTrue(
            preview(checkout(self.s)["items"], self.s["customer"], "TECH100K")["coupon_error"]
        )

    def test_first_order_includes_other_coupons_and_non_coupon_orders(self):
        self.coupon.first_order_only = True
        self.coupon.save()
        first = create_order(checkout(self.s), self.s["customer"], "no-coupon", "one")
        with self.assertRaises(BusinessError):
            self.place()
        transition_order(first.pk, "cancel", self.s["customer"], "Cancel unpaid")
        self.place()

    def test_invalid_or_changed_quote_rolls_back_stock_order_and_usage(self):
        for changes in [{"quoted_total": Decimal("1")}, {"coupon_code": "UNKNOWN"}]:
            data = {**checkout(self.s, coupon_code="TECH100K"), **changes}
            with self.assertRaises(BusinessError):
                create_order(data, self.s["customer"], "rollback", str(changes))
            self.assertEqual(Order.objects.count(), 0)
            self.assertEqual(CouponRedemption.objects.count(), 0)
            self.s["balance"].refresh_from_db()
            self.assertEqual(self.s["balance"].reserved, 0)

    def test_date_active_minimum_full_discount_and_global_limit(self):
        for field, value in [
            ("is_active", False),
            ("starts_at", timezone.now() + timedelta(hours=1)),
            ("ends_at", timezone.now() - timedelta(seconds=1)),
            ("min_subtotal", Decimal("2000000")),
            ("value", Decimal("9999999")),
        ]:
            previous = getattr(self.coupon, field)
            setattr(self.coupon, field, value)
            self.coupon.save()
            with self.assertRaises(BusinessError):
                self.place(key=field)
            setattr(self.coupon, field, previous)
            self.coupon.save()
        self.coupon.usage_limit = 1
        self.coupon.save()
        self.place()
        with self.assertRaises(BusinessError):
            create_order(checkout(self.s, coupon_code="TECH100K"), self.s["other"], "other", "one")

    def test_admin_permissions_csrf_and_configuration_validation(self):
        client = APIClient(enforce_csrf_checks=True)
        self.assertEqual(client.get("/api/v1/coupons/").status_code, 403)
        client.force_login(self.s["customer"])
        self.assertEqual(client.get("/api/v1/coupons/").status_code, 403)
        self.assertEqual(
            client.post(
                "/api/v1/checkout/promotions/", {"items": checkout(self.s)["items"]}, format="json"
            ).status_code,
            403,
        )
        client.force_login(self.s["admin"])
        token = client.get("/api/v1/auth/csrf/").json()["csrfToken"]
        path = f"/api/v1/coupons/{self.coupon.pk}/"
        self.assertEqual(
            client.patch(
                path,
                {"discount_type": "PERCENT", "value": 101},
                format="json",
                HTTP_X_CSRFTOKEN=token,
            ).status_code,
            400,
        )
        self.assertEqual(
            client.patch(
                path, {"code": "RENAME"}, format="json", HTTP_X_CSRFTOKEN=token
            ).status_code,
            400,
        )
        response = client.patch(path, {"is_active": False}, format="json", HTTP_X_CSRFTOKEN=token)
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(client.delete(path, HTTP_X_CSRFTOKEN=token).status_code, 405)

    @override_settings(
        APP_ENV="development",
        VNPAY_SANDBOX_ENABLED=True,
        VNPAY_TMN_CODE="TEST1234",
        VNPAY_HASH_SECRET="coupon-test-secret",
        VNPAY_RETURN_URL="http://localhost:5173/api/v1/payments/vnpay/return/",
        CUSTOMER_FRONTEND_URL="http://localhost:5173",
    )
    def test_vnpay_uses_discounted_amount_and_replay_does_not_consume_again(self):
        order = self.place(payment_method="VNPAY_SANDBOX")
        attempt = create_attempt(order.pk, self.s["customer"], "", "127.0.0.1")
        params = parse_qs(urlsplit(attempt.payment_url).query)
        self.assertEqual(params["vnp_Amount"], ["113400000"])
        data = {
            "vnp_TmnCode": "TEST1234",
            "vnp_TxnRef": attempt.reference.hex,
            "vnp_Amount": "113400000",
            "vnp_ResponseCode": "00",
            "vnp_TransactionStatus": "00",
            "vnp_TransactionNo": "11112222",
            "vnp_PayDate": timezone.now()
            .astimezone(ZoneInfo("Asia/Ho_Chi_Minh"))
            .strftime("%Y%m%d%H%M%S"),
            "vnp_BankCode": "NCB",
        }
        data["vnp_SecureHash"] = hmac.new(
            b"coupon-test-secret", urlencode(sorted(data.items())).encode(), hashlib.sha512
        ).hexdigest()
        from django.http import QueryDict

        query = QueryDict(urlencode(data))
        self.assertEqual(receive_ipn(query)["RspCode"], "00")
        self.assertEqual(receive_ipn(query)["RspCode"], "02")
        order.refresh_from_db()
        self.assertEqual(order.payment_status, "PAID")
        self.assertEqual(order.coupon_redemption.status, "USED")


class CouponConcurrencyTests(TransactionTestCase):
    def test_last_global_use_is_serialized_across_warehouses(self):
        s = scenario(quantity=10)
        coupon(usage_limit=1)
        second = ProductVariant.objects.create(
            product=s["p"], sku="SECOND", price=1234000, condition="New"
        )
        InventoryBalance.objects.create(warehouse=s["wb"], variant=second, on_hand=10)
        barrier = Barrier(2)

        def place(user_key, warehouse_key):
            close_old_connections()
            try:
                barrier.wait(timeout=10)
                items = [
                    {"variant": s["v"].pk if warehouse_key == "wa" else second.pk, "quantity": 1}
                ]
                order = create_order(
                    checkout(s, warehouse=s[warehouse_key].pk, coupon_code="TECH100K", items=items),
                    s[user_key],
                    user_key,
                    "concurrent",
                )
                return order.pk
            except BusinessError:
                return None
            finally:
                close_old_connections()

        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(
                pool.map(lambda args: place(*args), [("customer", "wa"), ("other", "wb")])
            )
        self.assertEqual(sum(r is not None for r in results), 1)
        self.assertEqual(CouponRedemption.objects.count(), 1)

    def test_first_order_coupon_cannot_be_used_in_parallel_orders_for_one_user(self):
        s = scenario(quantity=10)
        coupon(first_order_only=True, per_user_limit=2)
        second = ProductVariant.objects.create(
            product=s["p"], sku="SECOND", price=1234000, condition="New"
        )
        InventoryBalance.objects.create(warehouse=s["wb"], variant=second, on_hand=10)
        barrier = Barrier(2)

        def place(index):
            close_old_connections()
            try:
                barrier.wait(timeout=10)
                data = checkout(
                    s,
                    warehouse=s["wa" if index == 0 else "wb"].pk,
                    coupon_code="TECH100K",
                    items=[{"variant": s["v"].pk if index == 0 else second.pk, "quantity": 1}],
                )
                return create_order(data, s["customer"], "same-user", str(index)).pk
            except BusinessError:
                return None
            finally:
                close_old_connections()

        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(place, [0, 1]))
        self.assertEqual(sum(r is not None for r in results), 1)
        self.assertEqual(Order.objects.count(), 1)
