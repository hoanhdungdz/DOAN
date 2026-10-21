"""VNPAY sandbox: only verified IPN or signed server QueryDR can record money."""

import hashlib
import hmac
import ipaddress
import logging
import re
import uuid
from decimal import Decimal
from datetime import datetime, timedelta
from urllib.parse import parse_qs, urlencode, urlsplit
from zoneinfo import ZoneInfo

import requests

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from apps.inventory.services import lock_warehouses
from apps.orders.models import Order
from apps.orders.services import cancel_locked, is_expired
from common.audit import audit
from common.errors import BusinessError
from .models import PaymentTransaction, VnpayAttempt

PAYMENT_URL = "https://sandbox.vnpayment.vn/paymentv2/vpcpay.html"
QUERY_URL = "https://sandbox.vnpayment.vn/merchant_webapi/api/transaction"
QUERY_RESPONSE_FIELDS = (
    "vnp_ResponseId",
    "vnp_Command",
    "vnp_ResponseCode",
    "vnp_Message",
    "vnp_TmnCode",
    "vnp_TxnRef",
    "vnp_Amount",
    "vnp_BankCode",
    "vnp_PayDate",
    "vnp_TransactionNo",
    "vnp_TransactionType",
    "vnp_TransactionStatus",
    "vnp_OrderInfo",
    "vnp_PromotionCode",
    "vnp_PromotionAmount",
)
RETURN_PATH = "/api/v1/payments/vnpay/return/"
METHOD = "VNPAY_SANDBOX"
VIETNAM = ZoneInfo("Asia/Ho_Chi_Minh")


def ready():
    uri = urlsplit(settings.VNPAY_RETURN_URL)
    frontend = urlsplit(settings.CUSTOMER_FRONTEND_URL)
    return bool(
        settings.VNPAY_SANDBOX_ENABLED
        and settings.APP_ENV != "production"
        and settings.VNPAY_TMN_CODE
        and settings.VNPAY_HASH_SECRET
        and not uri.username
        and not uri.password
        and not uri.query
        and not uri.fragment
        and uri.path == RETURN_PATH
        and (uri.scheme, uri.netloc) == (frontend.scheme, frontend.netloc)
        and (
            uri.scheme == "https"
            or (uri.scheme == "http" and uri.hostname in ("localhost", "127.0.0.1"))
        )
    )


def encoded(values):
    return urlencode(sorted((k, str(v)) for k, v in values.items() if v != ""))


def signature(values):
    return hmac.new(
        settings.VNPAY_HASH_SECRET.encode(), encoded(values).encode(), hashlib.sha512
    ).hexdigest()


def verified_query(query):
    if not ready() or len(query.urlencode()) > 16000:
        return None
    data = {}
    for key, values in query.lists():
        if not key.startswith("vnp_"):
            continue
        if len(values) != 1 or len(values[0]) > 4096:
            return None
        data[key] = values[0]
    supplied = data.pop("vnp_SecureHash", "")
    data.pop("vnp_SecureHashType", None)
    if not re.fullmatch(r"[a-fA-F0-9]{128}", supplied) or not hmac.compare_digest(
        signature(data), supplied.lower()
    ):
        return None
    if data.get("vnp_TmnCode") != settings.VNPAY_TMN_CODE:
        return None
    return data


def public_attempt(attempt, include_url=False):
    data = {
        "reference": attempt.reference.hex,
        "order": attempt.order_id,
        "amount": str(attempt.amount),
        "status": attempt.status,
        "expires_at": attempt.expires_at,
        "response_code": attempt.response_code,
        "provider_transaction": attempt.provider_transaction,
        "review_reason": attempt.review_reason,
        "bank_mode": attempt.bank_mode,
        "promotion_code": attempt.promotion_code,
        "promotion_amount": str(attempt.promotion_amount),
        "customer_amount": str(attempt.amount - attempt.promotion_amount),
    }
    if include_url:
        data["payment_url"] = attempt.payment_url
    return data


def create_attempt(order_id, actor, bank_mode, client_ip):
    if not ready():
        raise BusinessError("VNPay sandbox chưa được cấu hình.", "VNPAY_NOT_CONFIGURED", 503)
    try:
        client_ip = str(ipaddress.ip_address(client_ip))
    except ValueError:
        client_ip = "127.0.0.1"
    expired = False
    with transaction.atomic():
        initial = Order.objects.get(pk=order_id, customer__user=actor)
        lock_warehouses(initial.warehouse_id)
        order = (
            Order.objects.select_for_update().select_related("warehouse__store").get(pk=initial.pk)
        )
        if order.payment_method != METHOD or order.channel != "ONLINE":
            raise BusinessError("Đơn này không dùng VNPay sandbox.", "INVALID_PAYMENT_METHOD")
        if is_expired(order):
            cancel_locked(order, None, "Hết hạn giữ hàng")
            expired = True
        elif order.payment_status != "UNPAID" or order.status not in (
            "PENDING",
            "CONFIRMED",
            "PACKING",
        ):
            raise BusinessError("Đơn không thể tạo thanh toán mới.", "INVALID_PAYMENT_STATE")
        else:
            now = timezone.now()
            pending = order.vnpay_attempts.filter(
                status="PENDING", expires_at__gt=now, bank_mode=bank_mode
            ).first()
            if pending:
                # Reuse duplicate clicks; an explicit mode change creates a distinct provider request.
                return pending
            amount = order.grand_total
            if (
                amount <= 0
                or amount != amount.to_integral_value()
                or len(str(int(amount * 100))) > 12
            ):
                raise BusinessError(
                    "Số tiền không nằm trong giới hạn VNPay hỗ trợ.", "INVALID_VNPAY_AMOUNT", 400
                )
            expires = (
                min(now + timedelta(minutes=15), order.expires_at)
                if order.expires_at
                else now + timedelta(minutes=15)
            )
            if expires <= now + timedelta(seconds=5):
                raise BusinessError("Đơn sắp hết hạn. Vui lòng kiểm tra lại đơn.", "ORDER_EXPIRING")
            ref = uuid.uuid4()
            values = {
                "vnp_Version": "2.1.0",
                "vnp_Command": "pay",
                "vnp_TmnCode": settings.VNPAY_TMN_CODE,
                "vnp_Amount": str(int(amount * 100)),
                "vnp_CurrCode": "VND",
                "vnp_TxnRef": ref.hex,
                "vnp_OrderInfo": "Thanh toan don hang " + order.code,
                "vnp_OrderType": "other",
                "vnp_Locale": "vn",
                "vnp_IpAddr": client_ip,
                "vnp_ReturnUrl": settings.VNPAY_RETURN_URL,
                "vnp_CreateDate": now.astimezone(VIETNAM).strftime("%Y%m%d%H%M%S"),
                "vnp_ExpireDate": expires.astimezone(VIETNAM).strftime("%Y%m%d%H%M%S"),
                "vnp_BankCode": bank_mode,
            }
            attempt = VnpayAttempt.objects.create(
                reference=ref,
                order=order,
                amount=amount,
                merchant=settings.VNPAY_TMN_CODE,
                bank_mode=bank_mode,
                expires_at=expires,
                payment_url=PAYMENT_URL
                + "?"
                + encoded(values)
                + "&vnp_SecureHash="
                + signature(values),
            )
            audit(
                actor,
                "payment.vnpay_created",
                attempt,
                order.warehouse.store,
                amount=str(amount),
                order=order.code,
            )
            return attempt
    if expired:
        raise BusinessError("Đơn đã hết hạn và được hủy.", "ORDER_EXPIRED")


def ipn_result(code):
    return {
        "RspCode": code,
        "Message": {
            "00": "Confirm Success",
            "01": "Order not found",
            "02": "Order already confirmed",
            "04": "Invalid amount",
            "97": "Invalid signature",
            "99": "Unable to process notification",
        }[code],
    }


def receive_ipn(query):
    data = verified_query(query)
    if data is None:
        return ipn_result("97")
    return apply_verified_payment(data)


def promotion_values(data, amount):
    """Provider amounts use VND x 100, including the provider-funded offer."""
    raw = data.get("vnp_PromotionAmount", "") or "0"
    code = data.get("vnp_PromotionCode", "")
    if (
        not re.fullmatch(r"[0-9]{1,20}", raw)
        or int(raw) % 100
        or int(raw) > int(amount * 100)
        or len(code) > 100
    ):
        raise ValueError("Invalid promotion")
    return code, Decimal(raw) / 100


def apply_verified_payment(data, source="ipn"):
    # Internal entry point: callers must authenticate the provider payload first.
    ref = data.get("vnp_TxnRef", "")
    if not re.fullmatch(r"[0-9a-f]{32}", ref):
        return ipn_result("01")
    initial = VnpayAttempt.objects.select_related("order").filter(pk=ref).first()
    if not initial:
        return ipn_result("01")
    try:
        with transaction.atomic():
            # Match the lock order used by checkout, expiration, cancellation and manual receipts.
            lock_warehouses(initial.order.warehouse_id)
            order = (
                Order.objects.select_for_update()
                .select_related("warehouse__store")
                .get(pk=initial.order_id)
            )
            attempt = VnpayAttempt.objects.select_for_update().get(pk=initial.pk)
            raw_amount = data.get("vnp_Amount", "")
            if (
                not re.fullmatch(r"[0-9]{1,20}", raw_amount)
                or int(raw_amount) != int(attempt.amount * 100)
                or attempt.amount != order.grand_total
                or attempt.merchant != data["vnp_TmnCode"]
                or order.payment_method != METHOD
            ):
                return ipn_result("04")
            code, status = data.get("vnp_ResponseCode", ""), data.get("vnp_TransactionStatus", "")
            if not re.fullmatch(r"[0-9]{2}", code) or not re.fullmatch(r"[0-9]{2}", status):
                return ipn_result("99")
            successful = code == "00" and status == "00"
            txn = data.get("vnp_TransactionNo", "")
            promo_code, promo_amount = promotion_values(data, attempt.amount)
            if attempt.transaction_id:
                if (
                    successful
                    and txn == attempt.provider_transaction
                    and ("vnp_PromotionAmount" in data or "vnp_PromotionCode" in data)
                ):
                    attempt.promotion_code, attempt.promotion_amount = promo_code, promo_amount
                    attempt.save(update_fields=["promotion_code", "promotion_amount"])
                return ipn_result(
                    "02" if not successful or txn == attempt.provider_transaction else "99"
                )
            if not successful:
                # A query may report pending, reversal, refund or unknown states. None
                # of these is permission to invent a capture or downgrade a paid order.
                if source == "querydr" and status != "02":
                    return ipn_result("02")
                if attempt.status == "FAILED":
                    return ipn_result("02")
                attempt.status, attempt.response_code = "FAILED", code
                attempt.notified_at = timezone.now()
                attempt.save(update_fields=["status", "response_code", "notified_at"])
                return ipn_result("00")
            if not re.fullmatch(r"[0-9]{1,100}", txn) or txn == "0":
                return ipn_result("99")
            paid = timezone.make_aware(
                datetime.strptime(data.get("vnp_PayDate", ""), "%Y%m%d%H%M%S"), VIETNAM
            )
            if paid < attempt.created_at - timedelta(
                minutes=1
            ) or paid > timezone.now() + timedelta(minutes=1):
                return ipn_result("99")
            # Expired/cancelled/duplicate captures are retained for reconciliation, never revive stock.
            reason = ""
            if is_expired(order):
                cancel_locked(order, None, "Hết hạn giữ hàng")
            if order.status == "CANCELLED" or paid > attempt.expires_at:
                reason = "Thanh toán về sau khi đơn/yêu cầu đã hết hạn hoặc bị hủy. Cần kiểm tra hoàn tiền."
            elif order.payment_status != "UNPAID":
                reason = (
                    "Có thêm giao dịch thành công cho đơn đã thanh toán. Cần kiểm tra hoàn tiền."
                )
            payment = PaymentTransaction.objects.create(
                order=order,
                actor=None,
                kind="CAPTURE",
                amount=attempt.amount,
                key="vnpay:" + attempt.reference.hex,
                reference="VNPAY-SANDBOX:" + txn,
            )
            attempt.provider_transaction, attempt.transaction = txn, payment
            attempt.response_code, attempt.bank_code = code, data.get("vnp_BankCode", "")[:30]
            attempt.review_reason, attempt.notified_at = reason, timezone.now()
            attempt.status = "REVIEW" if reason else "SUCCEEDED"
            attempt.promotion_code, attempt.promotion_amount = promo_code, promo_amount
            attempt.save()
            if not reason:
                order.payment_status, order.paid_at, order.expires_at = "PAID", paid, None
                order.reservations.filter(status="ACTIVE").update(expires_at=None)
                from apps.orders.promotions import use_coupon

                use_coupon(order)
            elif order.payment_status == "UNPAID":
                order.payment_status, order.paid_at = "REFUND_PENDING", paid
            order.save()
            audit(
                None,
                "payment.vnpay_review" if reason else "payment.vnpay_capture",
                attempt,
                order.warehouse.store,
                order=order.code,
                amount=str(attempt.amount),
                reference=txn,
                source=source,
            )
            return ipn_result("00")
    except Exception as exc:
        # Never log request URLs, signatures, banking details or the merchant secret.
        logging.getLogger("tech_retail.api").error("VNPay IPN failed type=%s", type(exc).__name__)
        return ipn_result("99")


def pipe_signature(values):
    return hmac.new(
        settings.VNPAY_HASH_SECRET.encode(), "|".join(values).encode(), hashlib.sha512
    ).hexdigest()


def check_attempt(attempt):
    """Owner-triggered recovery when IPN is delayed; never trust browser return data."""
    if not ready() or attempt.merchant != settings.VNPAY_TMN_CODE:
        raise BusinessError("VNPay sandbox chưa được cấu hình.", "VNPAY_NOT_CONFIGURED", 503)
    original = parse_qs(urlsplit(attempt.payment_url).query)
    transaction_date = original.get("vnp_CreateDate", [""])[0]
    if not re.fullmatch(r"[0-9]{14}", transaction_date):
        raise BusinessError("Thiếu thông tin gốc để tra cứu giao dịch.", "VNPAY_QUERY_INVALID", 409)
    body = {
        "vnp_RequestId": uuid.uuid4().hex,
        "vnp_Version": "2.1.0",
        "vnp_Command": "querydr",
        "vnp_TmnCode": attempt.merchant,
        "vnp_TxnRef": attempt.reference.hex,
        "vnp_TransactionDate": transaction_date,
        "vnp_CreateDate": timezone.now().astimezone(VIETNAM).strftime("%Y%m%d%H%M%S"),
        "vnp_IpAddr": "127.0.0.1",
        "vnp_OrderInfo": "Kiem tra thanh toan " + attempt.reference.hex,
    }
    body["vnp_SecureHash"] = pipe_signature(list(body.values()))
    try:
        # Fixed provider endpoint; redirects and oversized responses are rejected.
        with requests.post(
            QUERY_URL, json=body, timeout=(3, 10), allow_redirects=False, stream=True
        ) as response:
            response.raise_for_status()
            if response.status_code != 200:
                raise ValueError("Unexpected status")
            raw = bytearray()
            for chunk in response.iter_content(4096):
                raw.extend(chunk)
                if len(raw) > 32000:
                    raise ValueError("Oversized response")
        import json

        data = json.loads(raw)
        if not isinstance(data, dict) or any(not isinstance(v, str) for v in data.values()):
            raise ValueError("Invalid response")
    except requests.RequestException, ValueError, TypeError:
        raise BusinessError(
            "Chưa kết nối được VNPay. Vui lòng kiểm tra lại sau; không cần thanh toán lại.",
            "VNPAY_QUERY_UNAVAILABLE",
            503,
        ) from None
    supplied = data.get("vnp_SecureHash", "")
    if (
        not re.fullmatch(r"[a-fA-F0-9]{128}", supplied)
        or not hmac.compare_digest(
            pipe_signature([data.get(k, "") for k in QUERY_RESPONSE_FIELDS]), supplied.lower()
        )
        or data.get("vnp_Command") != "querydr"
        or data.get("vnp_TmnCode") != attempt.merchant
        or data.get("vnp_TxnRef") != attempt.reference.hex
    ):
        raise BusinessError("Không xác minh được phản hồi VNPay.", "VNPAY_QUERY_INVALID", 502)
    if data.get("vnp_ResponseCode") != "00":
        raise BusinessError(
            "VNPay chưa trả kết quả tra cứu. Vui lòng thử lại sau; không cần thanh toán lại.",
            "VNPAY_QUERY_UNAVAILABLE",
            503,
        )
    if data.get("vnp_TransactionType") != "01":
        raise BusinessError("Phản hồi không phải giao dịch thanh toán.", "VNPAY_QUERY_INVALID", 502)
    result = apply_verified_payment(data, source="querydr")
    if result["RspCode"] not in ("00", "02"):
        raise BusinessError(
            "Kết quả VNPay không khớp yêu cầu thanh toán.", "VNPAY_QUERY_INVALID", 502
        )
    attempt.refresh_from_db()
    return attempt
