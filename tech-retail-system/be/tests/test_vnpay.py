import hashlib
import hmac
import logging
import json
import uuid
from unittest.mock import MagicMock, patch
from datetime import timedelta
from urllib.parse import parse_qs, urlencode, urlsplit
from zoneinfo import ZoneInfo

from django.core.cache import cache
from django.test import TestCase, TransactionTestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from apps.orders.models import Order
from apps.orders.services import create_order, transition_order
from apps.payments.models import PaymentTransaction, VnpayAttempt
from common.logging import RedactOAuthQuery
from .factories import checkout, scenario

SECRET = "test-only-vnpay-secret"
RETURN = "https://shop.test.invalid/api/v1/payments/vnpay/return/"


@override_settings(
    VNPAY_SANDBOX_ENABLED=True,
    VNPAY_TMN_CODE="TEST1234",
    VNPAY_HASH_SECRET=SECRET,
    VNPAY_RETURN_URL=RETURN,
    CUSTOMER_FRONTEND_URL="https://shop.test.invalid",
)
class VnpayTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.s = scenario()

    def setUp(self):
        cache.clear()
        self.client = APIClient(enforce_csrf_checks=True)
        self.client.force_login(self.s["customer"])
        self.order = create_order(
            checkout(self.s, payment_method="VNPAY_SANDBOX"),
            self.s["customer"],
            "vnpay-test",
            "checkout",
        )

    def start(self, client=None, order=None, body=None):
        client = client or self.client
        token = client.get("/api/v1/auth/csrf/").json()["csrfToken"]
        return client.post(
            f"/api/v1/my-orders/{(order or self.order).pk}/vnpay/",
            body or {},
            format="json",
            HTTP_X_CSRFTOKEN=token,
        )

    def attempt(self):
        response = self.start()
        self.assertEqual(response.status_code, 200, response.content)
        self.assertNotIn(SECRET, response.content.decode())
        return VnpayAttempt.objects.get(pk=response.json()["reference"])

    def params(self, attempt, **changes):
        return {
            "vnp_TmnCode": "TEST1234",
            "vnp_TxnRef": attempt.reference.hex,
            "vnp_Amount": str(int(attempt.amount * 100)),
            "vnp_ResponseCode": "00",
            "vnp_TransactionStatus": "00",
            "vnp_TransactionNo": "123456789",
            "vnp_PayDate": timezone.now()
            .astimezone(ZoneInfo("Asia/Ho_Chi_Minh"))
            .strftime("%Y%m%d%H%M%S"),
            "vnp_BankCode": "NCB",
            "vnp_OrderInfo": "Thanh toan don hang test",
            **changes,
        }

    def signed(self, values):
        # Provider-side test fixture signs data independently of the application helper.
        raw = urlencode(sorted(values.items()))
        return {
            **values,
            "vnp_SecureHash": hmac.new(SECRET.encode(), raw.encode(), hashlib.sha512).hexdigest(),
        }

    def ipn(self, values):
        response = APIClient().get("/api/v1/payments/vnpay/ipn/", self.signed(values))
        self.assertEqual(response.status_code, 200)
        self.assertIn("no-store", response["Cache-Control"])
        return response.json()["RspCode"]

    def query_response(self, attempt, **changes):
        values = {
            **self.params(attempt),
            "vnp_ResponseId": "query-test",
            "vnp_Command": "querydr",
            "vnp_Message": "QueryDR success",
            "vnp_TransactionType": "01",
            **changes,
        }
        # Separate provider fixture: QueryDR uses positional pipe fields, not URL encoding.
        fields = "ResponseId Command ResponseCode Message TmnCode TxnRef Amount BankCode PayDate TransactionNo TransactionType TransactionStatus OrderInfo PromotionCode PromotionAmount".split()
        message = "|".join(values.get("vnp_" + field, "") for field in fields)
        values["vnp_SecureHash"] = hmac.new(
            SECRET.encode(), message.encode(), hashlib.sha512
        ).hexdigest()
        return values

    def query(self, attempt, values=None):
        response = MagicMock()
        response.status_code = 200
        response.iter_content.return_value = [
            json.dumps(values or self.query_response(attempt)).encode()
        ]
        response.__enter__.return_value = response
        path = f"/api/v1/payments/vnpay/attempts/{attempt.reference.hex}/check/"
        with patch("apps.payments.vnpay.requests.post", return_value=response) as post:
            result = self.client.post(
                path,
                {},
                format="json",
                HTTP_X_CSRFTOKEN=self.client.get("/api/v1/auth/csrf/").json()["csrfToken"],
            )
        return result, post

    def test_query_is_owner_post_csrf_only_and_get_stays_read_only(self):
        attempt = self.attempt()
        path = f"/api/v1/payments/vnpay/attempts/{attempt.reference.hex}/check/"
        with patch("apps.payments.vnpay.requests.post") as post:
            self.assertEqual(self.client.get(path).status_code, 405)
            self.assertEqual(self.client.post(path, {}, format="json").status_code, 403)
            self.client.force_login(self.s["admin"])
            response, _ = self.query(attempt)
            self.assertEqual(response.status_code, 404)
            self.assertNotIn("VnpayAttempt", response.content.decode())
            post.assert_not_called()
        self.assertFalse(PaymentTransaction.objects.exists())

    def test_query_recovers_ipn_once_and_signs_original_date_and_amount(self):
        attempt = self.attempt()
        values = self.query_response(attempt)
        response, post = self.query(attempt, values)
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(response.json()["order_payment_status"], "PAID")
        request = post.call_args.kwargs["json"]
        fields = "RequestId Version Command TmnCode TxnRef TransactionDate CreateDate IpAddr OrderInfo".split()
        message = "|".join(request["vnp_" + k] for k in fields)
        self.assertEqual(
            request["vnp_SecureHash"],
            hmac.new(SECRET.encode(), message.encode(), hashlib.sha512).hexdigest(),
        )
        self.assertEqual(
            request["vnp_TransactionDate"],
            parse_qs(urlsplit(attempt.payment_url).query)["vnp_CreateDate"][0],
        )
        self.assertFalse(post.call_args.kwargs["allow_redirects"])
        self.assertEqual(self.query(attempt, values)[0].status_code, 200)
        self.assertEqual(self.ipn(self.params(attempt)), "02")
        self.assertEqual(PaymentTransaction.objects.count(), 1)

    def test_query_combines_shop_and_provider_offers_without_reducing_capture_twice(self):
        from .test_coupons import coupon

        coupon()
        self.order = create_order(
            checkout(self.s, payment_method="VNPAY_SANDBOX", coupon_code="TECH100K"),
            self.s["customer"],
            "query",
            "coupon",
        )
        attempt = self.attempt()
        values = self.query_response(
            attempt, vnp_PromotionCode="CTT0604", vnp_PromotionAmount="10000000"
        )
        response, _ = self.query(attempt, values)
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(response.json()["promotion_amount"], "100000.00")
        self.assertEqual(response.json()["customer_amount"], "1034000.00")
        self.order.refresh_from_db()
        self.assertEqual(self.order.grand_total, 1134000)
        self.assertEqual(self.order.discount_total, 100000)
        self.assertEqual(self.order.coupon_redemption.status, "USED")
        self.assertEqual(PaymentTransaction.objects.get().amount, 1134000)
        # A duplicate IPN without promotion fields cannot erase a verified offer.
        self.assertEqual(self.ipn(self.params(attempt)), "02")
        attempt.refresh_from_db()
        self.assertEqual(attempt.promotion_amount, 100000)

    def test_query_rejects_forged_or_mismatched_provider_results(self):
        attempt = self.attempt()
        for changes in (
            {"vnp_TmnCode": "OTHER"},
            {"vnp_TxnRef": uuid.uuid4().hex},
            {"vnp_Amount": "100"},
            {"vnp_TransactionType": "02"},
            {"vnp_PromotionAmount": "99999999999999"},
            {"vnp_PayDate": "bad"},
        ):
            cache.clear()
            response, _ = self.query(attempt, self.query_response(attempt, **changes))
            self.assertEqual(response.status_code, 502, response.content)
        cache.clear()
        forged = self.query_response(attempt)
        forged["vnp_SecureHash"] = "0" * 128
        self.assertEqual(self.query(attempt, forged)[0].status_code, 502)
        self.assertFalse(PaymentTransaction.objects.exists())

    def test_query_pending_or_unavailable_does_not_capture(self):
        attempt = self.attempt()
        response, _ = self.query(attempt, self.query_response(attempt, vnp_TransactionStatus="01"))
        self.assertEqual(response.json()["status"], "PENDING")
        self.assertEqual(
            self.query(attempt, self.query_response(attempt, vnp_ResponseCode="91"))[0].status_code,
            503,
        )
        import requests

        with patch("apps.payments.vnpay.requests.post", side_effect=requests.Timeout):
            response = self.client.post(
                f"/api/v1/payments/vnpay/attempts/{attempt.reference.hex}/check/",
                {},
                format="json",
                HTTP_X_CSRFTOKEN=self.client.get("/api/v1/auth/csrf/").json()["csrfToken"],
            )
        self.assertEqual(response.status_code, 503)
        self.assertFalse(PaymentTransaction.objects.exists())

    def test_query_late_capture_keeps_cancelled_stock_released(self):
        attempt = self.attempt()
        transition_order(self.order.pk, "cancel", self.s["customer"], "Test cancel")
        response, _ = self.query(attempt)
        self.assertEqual(response.json()["status"], "REVIEW")
        self.assertEqual(response.json()["order_payment_status"], "REFUND_PENDING")
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, "CANCELLED")
        self.s["balance"].refresh_from_db()
        self.assertEqual(self.s["balance"].reserved, 0)

    def test_disabled_provider_does_not_create_attempt_or_accept_checkout(self):
        with override_settings(VNPAY_SANDBOX_ENABLED=False):
            self.assertFalse(self.client.get("/api/v1/features/").json()["vnpay_sandbox"])
            self.assertEqual(self.start().status_code, 503)
            response = self.client.post(
                "/api/v1/orders/",
                checkout(self.s, payment_method="VNPAY_SANDBOX"),
                format="json",
                HTTP_X_CSRFTOKEN=self.client.get("/api/v1/auth/csrf/").json()["csrfToken"],
                HTTP_IDEMPOTENCY_KEY="disabled",
            )
            self.assertEqual(response.status_code, 503)
        self.assertFalse(VnpayAttempt.objects.exists())

    def test_start_is_owner_only_post_csrf_protected_and_server_prices_amount(self):
        path = f"/api/v1/my-orders/{self.order.pk}/vnpay/"
        self.assertEqual(self.client.get(path).status_code, 405)
        self.assertEqual(self.client.post(path, {}, format="json").json()["code"], "CSRF_FAILED")
        anonymous = APIClient(enforce_csrf_checks=True)
        self.assertEqual(self.start(client=anonymous).status_code, 403)
        for user in [self.s["other"], self.s["admin"]]:
            other = APIClient(enforce_csrf_checks=True)
            other.force_login(user)
            self.assertEqual(self.start(client=other).status_code, 404)
        response = self.start(body={"amount": 1, "bank_mode": "VNPAYQR"})
        values = {
            k: v[0] for k, v in parse_qs(urlsplit(response.json()["payment_url"]).query).items()
        }
        self.assertEqual(values["vnp_Amount"], "123400000")
        self.assertEqual(values["vnp_BankCode"], "VNPAYQR")
        self.assertEqual(values["vnp_ReturnUrl"], RETURN)
        checksum = values.pop("vnp_SecureHash")
        self.assertEqual(checksum, self.signed(values)["vnp_SecureHash"])
        self.assertTrue(
            response.json()["payment_url"].startswith(
                "https://sandbox.vnpayment.vn/paymentv2/vpcpay.html?"
            )
        )

    def test_double_click_reuses_unexpired_request(self):
        attempt = self.attempt()
        self.assertEqual(
            self.start(body={"bank_mode": ""}).json()["reference"], attempt.reference.hex
        )
        self.assertEqual(VnpayAttempt.objects.count(), 1)

    def test_gateway_mode_omits_bank_code_and_explicit_mode_change_remains_idempotent(self):
        first = self.attempt()
        self.assertNotIn("vnp_BankCode", parse_qs(urlsplit(first.payment_url).query))
        other = self.start(body={"bank_mode": "VNPAYQR"}).json()["reference"]
        self.assertNotEqual(other, first.reference.hex)
        self.assertEqual(self.start().json()["reference"], first.reference.hex)
        self.assertEqual(VnpayAttempt.objects.count(), 2)

    def test_success_ipn_records_capture_once_without_shipping_or_expiring_paid_stock(self):
        attempt = self.attempt()
        values = self.params(attempt)
        self.assertEqual(self.ipn(values), "00")
        self.assertEqual(self.ipn(values), "02")
        self.order.refresh_from_db()
        attempt.refresh_from_db()
        self.assertEqual(self.order.payment_status, "PAID")
        self.assertEqual(self.order.status, "PENDING")
        self.assertIsNone(self.order.expires_at)
        self.assertIsNone(self.order.reservations.get().expires_at)
        self.assertEqual(attempt.status, "SUCCEEDED")
        self.assertEqual(PaymentTransaction.objects.count(), 1)
        self.assertIsNone(PaymentTransaction.objects.get().actor)
        self.s["balance"].refresh_from_db()
        self.assertEqual(self.s["balance"].on_hand, 10)
        self.assertEqual(self.s["balance"].reserved, 1)
        self.assertEqual(
            self.ipn(self.params(attempt, vnp_ResponseCode="24", vnp_TransactionStatus="02")), "02"
        )
        self.order.refresh_from_db()
        self.assertEqual(self.order.payment_status, "PAID")

    def test_valid_browser_return_is_read_only_and_forged_return_cannot_pay(self):
        attempt = self.attempt()
        response = APIClient().get(
            "/api/v1/payments/vnpay/return/", self.signed(self.params(attempt))
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(
            response["Location"], "/payments/vnpay/return?reference=" + attempt.reference.hex
        )
        self.assertEqual(response["Referrer-Policy"], "no-referrer")
        forged = APIClient().get(
            "/api/v1/payments/vnpay/return/",
            {"vnp_TxnRef": attempt.reference.hex, "vnp_ResponseCode": "00"},
        )
        self.assertIn("invalid=1", forged["Location"])
        self.order.refresh_from_db()
        self.assertEqual(self.order.payment_status, "UNPAID")
        self.assertFalse(PaymentTransaction.objects.exists())

    def test_signature_amount_merchant_reference_and_duplicate_parameters(self):
        attempt = self.attempt()
        values = self.params(attempt)
        signed = self.signed(values)
        signed["vnp_Amount"] = "1"
        self.assertEqual(
            APIClient().get("/api/v1/payments/vnpay/ipn/", signed).json()["RspCode"], "97"
        )
        self.assertEqual(self.ipn(self.params(attempt, vnp_Amount="100")), "04")
        self.assertEqual(self.ipn(self.params(attempt, vnp_TmnCode="FOREIGN")), "97")
        self.assertEqual(self.ipn(self.params(attempt, vnp_TxnRef=uuid.uuid4().hex)), "01")
        duplicate = urlencode(self.signed(values)) + "&vnp_Amount=1"
        self.assertEqual(
            APIClient().get("/api/v1/payments/vnpay/ipn/?" + duplicate).json()["RspCode"], "97"
        )
        self.assertFalse(PaymentTransaction.objects.exists())

    def test_status_never_discloses_other_customers_payment(self):
        attempt = self.attempt()
        path = f"/api/v1/payments/vnpay/attempts/{attempt.reference.hex}/"
        self.assertEqual(APIClient().get(path).status_code, 403)
        self.client.force_login(self.s["other"])
        self.assertEqual(self.client.get(path).status_code, 404)
        self.client.force_login(self.s["customer"])
        self.assertEqual(self.client.get(path).json()["order_payment_status"], "UNPAID")

    def test_failure_keeps_order_unpaid_and_retry_uses_new_reference(self):
        attempt = self.attempt()
        self.assertEqual(
            self.ipn(self.params(attempt, vnp_ResponseCode="24", vnp_TransactionStatus="02")), "00"
        )
        self.order.refresh_from_db()
        self.assertEqual(self.order.payment_status, "UNPAID")
        self.assertNotEqual(self.attempt().reference, attempt.reference)
        self.assertFalse(PaymentTransaction.objects.exists())

    def test_expired_order_cancels_and_releases_stock_before_start(self):
        Order.objects.filter(pk=self.order.pk).update(
            expires_at=timezone.now() - timedelta(seconds=1)
        )
        self.assertEqual(self.start().json()["code"], "ORDER_EXPIRED")
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, "CANCELLED")
        self.s["balance"].refresh_from_db()
        self.assertEqual(self.s["balance"].reserved, 0)

    def test_payment_after_cancel_or_expiration_is_retained_for_refund_review(self):
        attempt = self.attempt()
        transition_order(self.order.pk, "cancel", self.s["customer"], "Test cancel")
        self.assertEqual(self.ipn(self.params(attempt)), "00")
        self.order.refresh_from_db()
        attempt.refresh_from_db()
        self.assertEqual(self.order.status, "CANCELLED")
        self.assertEqual(self.order.payment_status, "REFUND_PENDING")
        self.assertEqual(attempt.status, "REVIEW")
        self.assertEqual(PaymentTransaction.objects.count(), 1)
        self.s["balance"].refresh_from_db()
        self.assertEqual(self.s["balance"].reserved, 0)

    def test_duplicate_charge_is_retained_and_flagged_without_replacing_first_payment(self):
        first = self.attempt()
        self.ipn(self.params(first, vnp_ResponseCode="24", vnp_TransactionStatus="02"))
        second = self.attempt()
        self.assertEqual(self.ipn(self.params(first)), "00")
        self.assertEqual(self.ipn(self.params(second, vnp_TransactionNo="987654321")), "00")
        second.refresh_from_db()
        self.assertEqual(second.status, "REVIEW")
        self.order.refresh_from_db()
        self.assertEqual(self.order.payment_status, "PAID")
        self.assertEqual(PaymentTransaction.objects.count(), 2)

    def test_transaction_number_cannot_be_reused_for_different_order(self):
        first = self.attempt()
        self.ipn(self.params(first))
        self.order = create_order(
            checkout(self.s, payment_method="VNPAY_SANDBOX"),
            self.s["customer"],
            "vnpay-test",
            "second-order",
        )
        second = self.attempt()
        self.assertEqual(self.ipn(self.params(second)), "99")
        self.order.refresh_from_db()
        self.assertEqual(self.order.payment_status, "UNPAID")
        self.assertEqual(PaymentTransaction.objects.count(), 1)

    def test_manual_capture_and_shipping_unpaid_vnpay_are_blocked(self):
        self.client.force_login(self.s["admin"])
        token = self.client.get("/api/v1/auth/csrf/").json()["csrfToken"]
        response = self.client.post(
            "/api/v1/payments/",
            {"order": self.order.pk, "kind": "CAPTURE", "reference": "fake"},
            format="json",
            HTTP_X_CSRFTOKEN=token,
            HTTP_IDEMPOTENCY_KEY="manual",
        )
        self.assertEqual(response.json()["code"], "PROVIDER_PAYMENT_REQUIRED")
        transition_order(self.order.pk, "confirm", self.s["admin"])
        transition_order(self.order.pk, "pack", self.s["admin"])
        from common.errors import BusinessError

        with self.assertRaises(BusinessError):
            transition_order(self.order.pk, "ship", self.s["admin"])

    def test_invalid_pay_date_and_production_never_capture(self):
        attempt = self.attempt()
        self.assertEqual(self.ipn(self.params(attempt, vnp_PayDate="bad")), "99")
        with override_settings(APP_ENV="production"):
            self.assertEqual(self.ipn(self.params(attempt)), "97")
            self.assertEqual(self.start().status_code, 503)
        self.assertFalse(PaymentTransaction.objects.exists())

    def test_callback_log_redacts_bank_data(self):
        for path in ["ipn", "return"]:
            record = logging.LogRecord(
                "django.server",
                logging.INFO,
                "",
                1,
                f'"GET /api/v1/payments/vnpay/{path}/?vnp_SecureHash=private&vnp_BankTranNo=bank-secret HTTP/1.1" 200',
                (),
                None,
            )
            RedactOAuthQuery().filter(record)
            self.assertNotIn("private", record.getMessage())
            self.assertNotIn("bank-secret", record.getMessage())


@override_settings(
    VNPAY_SANDBOX_ENABLED=True,
    VNPAY_TMN_CODE="TEST1234",
    VNPAY_HASH_SECRET=SECRET,
    VNPAY_RETURN_URL=RETURN,
    CUSTOMER_FRONTEND_URL="https://shop.test.invalid",
)
class VnpayConcurrencyTests(TransactionTestCase):
    def test_simultaneous_start_and_ipn_retries_are_serialized(self):
        import threading
        from concurrent.futures import ThreadPoolExecutor
        from django.db import connections
        from apps.accounts.models import User
        from apps.payments.vnpay import create_attempt

        s = scenario()
        order = create_order(
            checkout(s, payment_method="VNPAY_SANDBOX"), s["customer"], "concurrent-vnpay", "order"
        )
        barrier = threading.Barrier(2)

        def start(_):
            connections.close_all()
            try:
                actor = User.objects.get(pk=s["customer"].pk)
                barrier.wait(timeout=10)
                return create_attempt(order.pk, actor, "VNPAYQR", "127.0.0.1").reference.hex
            finally:
                connections.close_all()

        with ThreadPoolExecutor(max_workers=2) as pool:
            refs = list(pool.map(start, [1, 2]))
        self.assertEqual(refs[0], refs[1])
        self.assertEqual(VnpayAttempt.objects.count(), 1)
        values = {
            "vnp_TmnCode": "TEST1234",
            "vnp_TxnRef": refs[0],
            "vnp_Amount": "123400000",
            "vnp_ResponseCode": "00",
            "vnp_TransactionStatus": "00",
            "vnp_TransactionNo": "1234567",
            "vnp_PayDate": timezone.now()
            .astimezone(ZoneInfo("Asia/Ho_Chi_Minh"))
            .strftime("%Y%m%d%H%M%S"),
        }
        values["vnp_SecureHash"] = hmac.new(
            SECRET.encode(), urlencode(sorted(values.items())).encode(), hashlib.sha512
        ).hexdigest()
        barrier = threading.Barrier(2)

        def notify(_):
            connections.close_all()
            try:
                barrier.wait(timeout=10)
                return APIClient().get("/api/v1/payments/vnpay/ipn/", values).json()["RspCode"]
            finally:
                connections.close_all()

        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(notify, [1, 2]))
        self.assertCountEqual(results, ["00", "02"])
        self.assertEqual(PaymentTransaction.objects.count(), 1)
