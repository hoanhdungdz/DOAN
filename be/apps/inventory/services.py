from django.db import transaction
from django.utils import timezone
from common.errors import BusinessError
from common.audit import audit
from apps.accounts.permissions import require
from apps.stores.models import Warehouse
from .models import (
    InventoryBalance,
    InventoryReservation,
    ReservationHistory,
    StockMovement,
    StockDocument,
    StockTransfer,
)


def lock_warehouses(*ids):
    locked = list(
        Warehouse.objects.select_for_update().filter(pk__in=sorted(set(ids))).order_by("pk")
    )
    if len(locked) != len(set(ids)) or any(
        not w.is_active or not w.store.is_active for w in locked
    ):
        raise BusinessError("Kho không hoạt động hoặc không tồn tại.", "WAREHOUSE_UNAVAILABLE", 400)
    return locked


def balance_for(warehouse, variant):
    # Caller holds warehouse lock, serializing creation as well as changes.
    b, _ = InventoryBalance.objects.get_or_create(warehouse_id=warehouse, variant_id=variant)
    return InventoryBalance.objects.select_for_update().get(pk=b.pk)


def movement(balance, delta, kind, reference, actor=None):
    if balance.on_hand + delta < balance.reserved:
        raise BusinessError("Không đủ tồn khả dụng.", "INSUFFICIENT_STOCK")
    balance.on_hand += delta
    balance.save(update_fields=["on_hand", "reserved", "updated_at"])
    StockMovement.objects.create(
        balance=balance,
        delta=delta,
        on_hand_after=balance.on_hand,
        kind=kind,
        reference=str(reference),
        actor=actor if actor and actor.is_authenticated else None,
    )


def reserve(balance, quantity, order=None, transfer=None, expires=None):
    if balance.available < quantity:
        raise BusinessError("Không đủ tồn khả dụng.", "INSUFFICIENT_STOCK")
    balance.reserved += quantity
    balance.save(update_fields=["reserved", "updated_at"])
    r = InventoryReservation.objects.create(
        balance=balance, quantity=quantity, order=order, transfer=transfer, expires_at=expires
    )
    ReservationHistory.objects.create(reservation=r, status="ACTIVE")
    return r


def release_reservations(source, consume=False, actor=None, kind="SALE"):
    for r in (
        source.reservations.select_for_update()
        .filter(status="ACTIVE")
        .order_by("balance__variant_id")
    ):
        b = InventoryBalance.objects.select_for_update().get(pk=r.balance_id)
        b.reserved -= r.quantity
        if consume:
            movement(b, -r.quantity, kind, source.pk, actor)
        else:
            b.save(update_fields=["reserved", "updated_at"])
        r.status = "CONSUMED" if consume else "RELEASED"
        r.save(update_fields=["status", "updated_at"])
        ReservationHistory.objects.create(reservation=r, status=r.status)


@transaction.atomic
def post_document(document_id, actor, cancel=False):
    initial = StockDocument.objects.get(pk=document_id)
    lock_warehouses(initial.warehouse_id)
    doc = (
        StockDocument.objects.select_for_update()
        .select_related("warehouse__store")
        .get(pk=document_id)
    )
    require(actor, "manage_stock", doc.warehouse.store_id)
    target = "CANCELLED" if cancel else "POSTED"
    if doc.status == target:
        return doc
    if doc.status != "DRAFT":
        raise BusinessError("Chứng từ đã ghi sổ/hủy không thể sửa.", "INVALID_TRANSITION")
    if not cancel:
        if not doc.items.exists():
            raise BusinessError("Chứng từ phải có dòng hàng.", "EMPTY_DOCUMENT", 400)
        for item in doc.items.order_by("variant_id"):
            delta = item.quantity if doc.kind in ("IN", "ADJUST") else -item.quantity
            if doc.kind != "ADJUST" and item.quantity <= 0:
                raise BusinessError("Số lượng phải dương.", "INVALID_QUANTITY", 400)
            movement(
                balance_for(doc.warehouse_id, item.variant_id),
                delta,
                doc.kind,
                f"DOC:{doc.pk}",
                actor,
            )
        doc.posted_at = timezone.now()
        doc.posted_by = actor
    doc.status = target
    doc.save()
    audit(actor, "stock_document." + target.lower(), doc, doc.warehouse.store)
    return doc


@transaction.atomic
def transition_transfer(transfer_id, action, actor):
    initial = StockTransfer.objects.get(pk=transfer_id)
    lock_warehouses(initial.source_id, initial.destination_id)
    t = (
        StockTransfer.objects.select_for_update()
        .select_related("source__store", "destination__store")
        .get(pk=transfer_id)
    )
    require(
        actor, "manage_stock", t.destination.store_id if action == "receive" else t.source.store_id
    )
    transitions = {
        "approve": ("DRAFT", "APPROVED"),
        "dispatch": ("APPROVED", "IN_TRANSIT"),
        "receive": ("IN_TRANSIT", "RECEIVED"),
    }
    if action == "cancel":
        if t.status == "CANCELLED":
            return t
        if t.status not in ("DRAFT", "APPROVED"):
            raise BusinessError("Chỉ hủy điều chuyển trước xuất.", "INVALID_TRANSITION")
        release_reservations(t)
        t.status = "CANCELLED"
    else:
        before, after = transitions[action]
        if t.status == after:
            return t
        if t.status != before:
            raise BusinessError("Trạng thái điều chuyển không hợp lệ.", "INVALID_TRANSITION")
        if not t.items.exists():
            raise BusinessError("Điều chuyển phải có dòng hàng.", "EMPTY_TRANSFER", 400)
        if action == "approve":
            for item in t.items.order_by("variant_id"):
                reserve(balance_for(t.source_id, item.variant_id), item.quantity, transfer=t)
            t.approved_at = timezone.now()
        elif action == "dispatch":
            release_reservations(t, consume=True, actor=actor, kind="TRANSFER_OUT")
            t.dispatched_at = timezone.now()
        else:
            for item in t.items.order_by("variant_id"):
                movement(
                    balance_for(t.destination_id, item.variant_id),
                    item.quantity,
                    "TRANSFER_IN",
                    t.pk,
                    actor,
                )
            t.received_at = timezone.now()
        t.status = after
    t.save()
    audit(actor, "transfer." + action, t, t.source.store, destination_store=t.destination.store_id)
    return t
