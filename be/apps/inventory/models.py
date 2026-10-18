from django.conf import settings
from django.db import models
from django.db.models import Q, F
from common.models import Timestamped


class InventoryBalance(Timestamped):
    warehouse = models.ForeignKey(
        "stores.Warehouse", on_delete=models.PROTECT, related_name="balances"
    )
    variant = models.ForeignKey(
        "products.ProductVariant", on_delete=models.PROTECT, related_name="balances"
    )
    on_hand = models.PositiveIntegerField(default=0)
    reserved = models.PositiveIntegerField(default=0)
    alert_threshold = models.PositiveIntegerField(default=3)

    @property
    def available(self):
        return self.on_hand - self.reserved

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["warehouse", "variant"], name="balance_warehouse_variant"
            ),
            models.CheckConstraint(
                condition=Q(on_hand__gte=F("reserved")), name="balance_reserved_lte_onhand"
            ),
        ]


class StockDocument(Timestamped):
    warehouse = models.ForeignKey("stores.Warehouse", on_delete=models.PROTECT)
    supplier = models.ForeignKey(
        "suppliers.Supplier", null=True, blank=True, on_delete=models.PROTECT
    )
    kind = models.CharField(max_length=10, choices=[(x, x) for x in ["IN", "OUT", "ADJUST"]])
    status = models.CharField(max_length=15, default="DRAFT")
    reason = models.CharField(max_length=500)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="+"
    )
    posted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, on_delete=models.PROTECT, related_name="+"
    )
    posted_at = models.DateTimeField(null=True)


class StockDocumentItem(models.Model):
    document = models.ForeignKey(StockDocument, on_delete=models.CASCADE, related_name="items")
    variant = models.ForeignKey("products.ProductVariant", on_delete=models.PROTECT)
    quantity = models.IntegerField()

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["document", "variant"], name="document_variant"),
            models.CheckConstraint(condition=~Q(quantity=0), name="document_nonzero_quantity"),
        ]


class StockTransfer(Timestamped):
    source = models.ForeignKey(
        "stores.Warehouse", on_delete=models.PROTECT, related_name="outgoing_transfers"
    )
    destination = models.ForeignKey(
        "stores.Warehouse", on_delete=models.PROTECT, related_name="incoming_transfers"
    )
    status = models.CharField(max_length=15, default="DRAFT")
    reason = models.CharField(max_length=500)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    approved_at = models.DateTimeField(null=True)
    dispatched_at = models.DateTimeField(null=True)
    received_at = models.DateTimeField(null=True)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=~Q(source=F("destination")), name="transfer_different_warehouses"
            )
        ]


class StockTransferItem(models.Model):
    transfer = models.ForeignKey(StockTransfer, on_delete=models.CASCADE, related_name="items")
    variant = models.ForeignKey("products.ProductVariant", on_delete=models.PROTECT)
    quantity = models.PositiveIntegerField()

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["transfer", "variant"], name="transfer_variant"),
            models.CheckConstraint(condition=Q(quantity__gt=0), name="transfer_positive_quantity"),
        ]


class InventoryReservation(Timestamped):
    balance = models.ForeignKey(
        InventoryBalance, on_delete=models.PROTECT, related_name="reservations"
    )
    order = models.ForeignKey(
        "orders.Order", null=True, on_delete=models.PROTECT, related_name="reservations"
    )
    transfer = models.ForeignKey(
        StockTransfer, null=True, on_delete=models.PROTECT, related_name="reservations"
    )
    quantity = models.PositiveIntegerField()
    status = models.CharField(max_length=15, default="ACTIVE")
    expires_at = models.DateTimeField(null=True)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=(
                    Q(order__isnull=False, transfer__isnull=True)
                    | Q(order__isnull=True, transfer__isnull=False)
                ),
                name="reservation_exactly_one_source",
            ),
            models.CheckConstraint(
                condition=Q(quantity__gt=0), name="reservation_quantity_positive"
            ),
        ]
        indexes = [models.Index(fields=["status", "expires_at"])]


class ReservationHistory(models.Model):
    reservation = models.ForeignKey(
        InventoryReservation, on_delete=models.PROTECT, related_name="history"
    )
    status = models.CharField(max_length=15)
    created_at = models.DateTimeField(auto_now_add=True)


class StockMovement(models.Model):
    balance = models.ForeignKey(
        InventoryBalance, on_delete=models.PROTECT, related_name="movements"
    )
    delta = models.IntegerField()
    on_hand_after = models.PositiveIntegerField()
    kind = models.CharField(max_length=30)
    reference = models.CharField(max_length=100)
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.PROTECT)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["balance", "kind", "reference"], name="movement_unique_source"
            )
        ]
        indexes = [models.Index(fields=["balance", "created_at"])]
