from django.db import transaction
from django.utils import timezone
from common.errors import BusinessError
from common.audit import audit
from apps.accounts.permissions import require
from apps.inventory.services import lock_warehouses
from apps.orders.models import Order
from apps.orders.services import is_expired, cancel_locked
from .models import PaymentTransaction


def payment_locked(order, actor, kind, key, reference=""):
    require(actor, "manage_payments", order.warehouse.store_id)
    if not key or len(key) > 100:
        raise BusinessError("Cần Idempotency-Key hợp lệ.", "IDEMPOTENCY_REQUIRED", 400)
    existing = order.transactions.filter(key=key).first()
    if existing:
        if existing.kind != kind or existing.reference != reference:
            raise BusinessError("Key thanh toán có nội dung khác.", "IDEMPOTENCY_MISMATCH")
        return existing
    if kind == "CAPTURE":
        if order.status == "CANCELLED" or order.payment_status != "UNPAID":
            raise BusinessError("Đơn không thể ghi nhận thu tiền.", "INVALID_PAYMENT_STATE")
        if order.payment_method == "BANK_TRANSFER" and not reference.strip():
            raise BusinessError("Chuyển khoản cần tham chiếu xác nhận.", "REFERENCE_REQUIRED", 400)
        order.payment_status = "PAID"
        order.paid_at = timezone.now()
    else:
        if order.payment_status != "REFUND_PENDING" or not reference.strip():
            raise BusinessError(
                "Chỉ hoàn khi có nghĩa vụ hoàn và tham chiếu.", "INVALID_REFUND_STATE"
            )
        order.payment_status = "REFUNDED"
    payment = PaymentTransaction.objects.create(
        order=order, actor=actor, kind=kind, amount=order.grand_total, key=key, reference=reference
    )
    order.save()
    audit(
        actor,
        "payment." + kind.lower(),
        payment,
        order.warehouse.store,
        amount=str(payment.amount),
        order=order.code,
    )
    return payment


def record_payment(order_id, actor, kind, key, reference=""):
    expired = False
    with transaction.atomic():
        initial = Order.objects.get(pk=order_id)
        lock_warehouses(initial.warehouse_id)
        order = (
            Order.objects.select_for_update().select_related("warehouse__store").get(pk=order_id)
        )
        require(actor, "manage_payments", order.warehouse.store_id)
        if order.channel == "IN_STORE" and order.status == "DRAFT" and kind == "CAPTURE":
            raise BusinessError(
                "Đơn tại quầy cần chốt bán để thu tiền và xuất kho đồng thời.",
                "POS_FINISH_REQUIRED",
            )
        if is_expired(order):
            cancel_locked(order, None, "Hết hạn giữ hàng")
            expired = True
        else:
            payment = payment_locked(order, actor, kind, key, reference)
    if expired:
        raise BusinessError("Đơn đã hết hạn và được hủy.", "ORDER_EXPIRED")
    return payment
