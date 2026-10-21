import hashlib
import json
from datetime import timedelta
from decimal import Decimal
from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils import timezone
from common.audit import audit
from common.errors import BusinessError
from common.models import IdempotencyRecord
from apps.accounts.permissions import require, is_admin
from apps.customers.models import Customer
from apps.products.models import ProductVariant
from apps.inventory.services import (
    lock_warehouses,
    balance_for,
    reserve,
    release_reservations,
    movement,
)
from .models import Order, OrderItem, OrderStatusHistory, Invoice
from .promotions import reserve_coupon, release_coupon


def history(order, status, actor=None, reason=""):
    order.status = status
    order.save()
    OrderStatusHistory.objects.create(
        order=order,
        status=status,
        actor=actor if actor and actor.is_authenticated else None,
        reason=reason,
    )
    audit(actor, "order." + status.lower(), order, order.warehouse.store, reason=reason)


def invoice_for(order):
    return Invoice.objects.get_or_create(
        order=order,
        defaults={
            "code": "INV-" + order.code,
            "snapshot": {
                "code": order.code,
                "recipient_name": order.recipient_name,
                "store": order.warehouse.store.name,
                "seller": order.seller.full_name if order.seller else "",
                "total": str(order.grand_total),
                "subtotal": str(order.subtotal),
                "discount_total": str(order.discount_total),
                "coupon_code": order.coupon_code,
                "shipping_fee": str(order.shipping_fee),
                "items": [
                    {
                        "name": i.name,
                        "sku": i.sku,
                        "quantity": i.quantity,
                        "unit_price": str(i.unit_price),
                        "line_total": str(i.line_total),
                    }
                    for i in order.items.all()
                ],
            },
        },
    )[0]


def cancel_locked(order, actor=None, reason=""):
    release_reservations(order)
    release_coupon(order)
    if order.payment_status == "PAID":
        order.payment_status = "REFUND_PENDING"
    history(order, "CANCELLED", actor, reason)


def is_expired(order):
    return order.status == "PENDING" and order.expires_at and order.expires_at <= timezone.now()


@transaction.atomic
def create_order(data, actor, scope, key):
    if not key or len(key) > 100:
        raise BusinessError("Cần Idempotency-Key (tối đa 100 ký tự).", "IDEMPOTENCY_REQUIRED", 400)
    fingerprint = hashlib.sha256(json.dumps(data, sort_keys=True, default=str).encode()).hexdigest()
    # Unique row serializes retries even when different warehouses are submitted.
    record, _ = IdempotencyRecord.objects.get_or_create(
        scope=scope, key=key, defaults={"fingerprint": fingerprint}
    )
    record = IdempotencyRecord.objects.select_for_update().get(pk=record.pk)
    if record.fingerprint != fingerprint:
        raise BusinessError("Key đã dùng với nội dung khác.", "IDEMPOTENCY_MISMATCH")
    if record.order_id:
        lock_warehouses(record.order.warehouse_id)
        previous = (
            Order.objects.select_for_update()
            .select_related("warehouse__store")
            .get(pk=record.order_id)
        )
        if is_expired(previous):
            cancel_locked(previous, None, "Hết hạn giữ hàng")
        return previous
    channel = data.get("channel", "ONLINE")
    if channel == "ONLINE" and actor.is_authenticated:
        # Serialize first-order eligibility, including concurrent orders without
        # a coupon. Other order paths never acquire this lock after a warehouse.
        get_user_model().objects.select_for_update().get(pk=actor.pk)
    if data.get("coupon_code") and channel != "ONLINE":
        raise BusinessError("Mã cửa hàng hiện áp dụng cho đơn online.", "COUPON_INVALID", 400)
    warehouse = lock_warehouses(data["warehouse"])[0]
    for old in (
        Order.objects.select_for_update()
        .filter(warehouse=warehouse, status="PENDING", expires_at__lte=timezone.now())
        .order_by("pk")
    ):
        cancel_locked(old, None, "Hết hạn giữ hàng")
    channel = data.get("channel", "ONLINE")
    if data["payment_method"] == "VNPAY_SANDBOX":
        from apps.payments.vnpay import ready

        if channel != "ONLINE" or not ready():
            raise BusinessError(
                "VNPay sandbox chưa khả dụng cho đơn này.", "VNPAY_NOT_CONFIGURED", 503
            )
    if channel == "IN_STORE":
        require(actor, "manage_sales", warehouse.store_id)
    if channel == "ONLINE" and data["payment_method"] == "CASH":
        raise BusinessError("Tiền mặt chỉ dùng tại quầy.", "INVALID_PAYMENT", 400)
    if channel == "IN_STORE" and data["payment_method"] == "COD":
        raise BusinessError("COD chỉ dùng online.", "INVALID_PAYMENT", 400)
    if channel == "IN_STORE" and data.get("customer"):
        customers = Customer.objects.all()
        if not is_admin(actor):
            customers = customers.filter(order__warehouse__store_id=warehouse.store_id).distinct()
        customer = customers.filter(pk=data["customer"]).first()
        if customer is None:
            raise BusinessError(
                "Không tìm thấy hồ sơ khách trong phạm vi chi nhánh.", "CUSTOMER_UNAVAILABLE", 404
            )
    elif actor.is_authenticated and channel == "ONLINE":
        customer, _ = Customer.objects.get_or_create(
            user=actor,
            defaults={"name": actor.full_name or data["recipient_name"], "email": actor.email},
        )
    else:
        customer = Customer.objects.create(
            name=data["recipient_name"], phone=data["phone"], address=data.get("address", "")
        )
    order = Order.objects.create(
        customer=customer,
        warehouse=warehouse,
        seller=actor if channel == "IN_STORE" else None,
        channel=channel,
        status="DRAFT" if channel == "IN_STORE" else "PENDING",
        payment_method=data["payment_method"],
        recipient_name=data["recipient_name"],
        phone=data["phone"],
        address=data.get("address", ""),
        fulfillment=data["fulfillment"],
        expires_at=timezone.now() + timedelta(minutes=settings.ORDER_PENDING_TTL_MINUTES)
        if channel == "ONLINE"
        else None,
    )
    total = Decimal("0")
    coupon_lines = []
    for row in sorted(data["items"], key=lambda r: r["variant"]):
        variant = (
            ProductVariant.objects.select_for_update()
            .select_related("product")
            .filter(
                pk=row["variant"],
                is_active=True,
                product__is_active=True,
                product__category__is_active=True,
                product__brand__is_active=True,
            )
            .first()
        )
        if not variant:
            raise BusinessError("Sản phẩm không còn bán.", "VARIANT_UNAVAILABLE", 400)
        q = row["quantity"]
        line = variant.price * q
        total += line
        coupon_lines.append((variant.product.category_id, line))
        OrderItem.objects.create(
            order=order,
            variant=variant,
            name=variant.product.name,
            sku=variant.sku,
            attributes={"condition": variant.condition, **variant.attributes},
            quantity=q,
            unit_price=variant.price,
            line_total=line,
        )
        if channel == "ONLINE":
            balance = balance_for(warehouse.pk, variant.pk)
            if balance.available < q:
                raise BusinessError(
                    f"{variant.product.name}: {warehouse.store.name} chỉ còn {balance.available}, "
                    f"bạn cần {q}. Vui lòng chọn chi nhánh khác hoặc giảm số lượng.",
                    "INSUFFICIENT_STOCK",
                )
            reserve(balance, q, order=order, expires=order.expires_at)
    order.subtotal = total
    if data.get("coupon_code"):
        reserve_coupon(order, actor, coupon_lines, data["coupon_code"].strip().upper())
    order.grand_total = total - order.discount_total + order.shipping_fee
    if data.get("quoted_total") is not None and order.grand_total != data["quoted_total"]:
        raise BusinessError(
            "Giá hoặc ưu đãi đã thay đổi. Vui lòng kiểm tra tổng tiền và xác nhận lại.",
            "PRICE_CHANGED",
            409,
        )
    order.save()
    history(order, order.status, actor)
    record.order = order
    record.save(update_fields=["order"])
    return order


def _transition_locked(order, action, actor, reason):
    owner = actor and actor.is_authenticated and order.customer.user_id == actor.pk
    if action == "cancel" and owner and order.status in ("PENDING", "CANCELLED"):
        pass
    else:
        require(actor, "manage_sales", order.warehouse.store_id)
    if action == "cancel":
        if order.status == "CANCELLED":
            return order
        if order.status not in ("DRAFT", "PENDING", "CONFIRMED", "PACKING"):
            raise BusinessError("Không thể hủy sau khi xuất hàng.", "INVALID_TRANSITION")
        if not reason.strip():
            raise BusinessError("Vui lòng nhập lý do hủy.", "REASON_REQUIRED", 400)
        cancel_locked(order, actor, reason)
        return order
    transitions = {
        "confirm": ("PENDING", "CONFIRMED"),
        "pack": ("CONFIRMED", "PACKING"),
        "ship": ("PACKING", "SHIPPED"),
        "complete": ("SHIPPED", "COMPLETED"),
    }
    before, after = transitions[action]
    if order.status == after:
        return order
    if order.status != before:
        raise BusinessError("Không thể chuyển trạng thái đơn như yêu cầu.", "INVALID_TRANSITION")
    if action == "confirm":
        order.reservations.filter(status="ACTIVE").update(expires_at=None)
    if action == "ship":
        if order.payment_method == "VNPAY_SANDBOX" and order.payment_status != "PAID":
            raise BusinessError(
                "Đơn VNPay cần thanh toán thành công trước khi xuất giao.", "PAYMENT_REQUIRED"
            )
        release_reservations(order, True, actor)
    if action == "complete":
        if order.payment_status != "PAID":
            raise BusinessError("Chưa xác nhận thu tiền.", "PAYMENT_REQUIRED")
        order.completed_at = timezone.now()
    history(order, after, actor, reason)
    if action == "complete":
        invoice_for(order)
    return order


def transition_order(order_id, action, actor, reason=""):
    expired = False
    with transaction.atomic():
        initial = Order.objects.get(pk=order_id)
        lock_warehouses(initial.warehouse_id)
        order = (
            Order.objects.select_for_update()
            .select_related("customer", "warehouse__store")
            .get(pk=order_id)
        )
        # Check authorization before persisting expiration for externally supplied IDs.
        if not (
            action == "cancel" and actor.is_authenticated and order.customer.user_id == actor.pk
        ):
            require(actor, "manage_sales", order.warehouse.store_id)
        if is_expired(order):
            cancel_locked(order, None, "Hết hạn giữ hàng")
            expired = True
        else:
            _transition_locked(order, action, actor, reason)
    if expired:
        raise BusinessError("Đơn đã hết hạn và được hủy.", "ORDER_EXPIRED")
    return order


def finish_pos(order_id, actor, key, reference=""):
    with transaction.atomic():
        initial = Order.objects.get(pk=order_id)
        lock_warehouses(initial.warehouse_id)
        order = (
            Order.objects.select_for_update().select_related("warehouse__store").get(pk=order_id)
        )
        require(actor, "manage_sales", order.warehouse.store_id)
        require(actor, "manage_payments", order.warehouse.store_id)
        if order.channel != "IN_STORE":
            raise BusinessError("Chỉ chốt đơn tại quầy.", "INVALID_CHANNEL")
        if order.status == "COMPLETED":
            from apps.payments.services import payment_locked

            payment_locked(order, actor, "CAPTURE", key, reference)
            return order
        if order.status != "DRAFT":
            raise BusinessError("Đơn không còn đang soạn.", "INVALID_TRANSITION")
        for item in order.items.order_by("variant_id"):
            movement(
                balance_for(order.warehouse_id, item.variant_id),
                -item.quantity,
                "POS",
                order.pk,
                actor,
            )
        from apps.payments.services import payment_locked

        payment_locked(order, actor, "CAPTURE", key, reference)
        order.completed_at = timezone.now()
        history(order, "COMPLETED", actor)
        invoice_for(order)
        return order


def expire_orders(warehouse_ids=None):
    count = 0
    expired = Order.objects.filter(status="PENDING", expires_at__lte=timezone.now())
    if warehouse_ids is not None:
        expired = expired.filter(warehouse_id__in=warehouse_ids)
    ids = list(expired.values_list("id", flat=True))
    for pk in ids:
        with transaction.atomic():
            initial = Order.objects.get(pk=pk)
            lock_warehouses(initial.warehouse_id)
            order = Order.objects.select_for_update().select_related("warehouse__store").get(pk=pk)
            if is_expired(order):
                cancel_locked(order, None, "Hết hạn giữ hàng")
                count += 1
    return count
