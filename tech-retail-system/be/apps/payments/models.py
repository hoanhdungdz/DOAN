import uuid
from django.db import models
from django.conf import settings


class PaymentTransaction(models.Model):
    order = models.ForeignKey("orders.Order", on_delete=models.PROTECT, related_name="transactions")
    kind = models.CharField(
        max_length=15, choices=[("CAPTURE", "Thu tiền"), ("REFUND", "Hoàn tiền")]
    )
    amount = models.DecimalField(max_digits=18, decimal_places=2)
    key = models.CharField(max_length=100)
    reference = models.CharField(max_length=200, blank=True)
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.PROTECT)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["order", "key"], name="payment_order_key"),
            models.CheckConstraint(
                condition=models.Q(amount__gt=0), name="payment_amount_positive"
            ),
        ]


class VnpayAttempt(models.Model):
    reference = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    order = models.ForeignKey(
        "orders.Order", on_delete=models.PROTECT, related_name="vnpay_attempts"
    )
    amount = models.DecimalField(max_digits=18, decimal_places=2)
    merchant = models.CharField(max_length=32)
    bank_mode = models.CharField(max_length=10, default="VNPAYQR")
    status = models.CharField(
        max_length=12,
        default="PENDING",
        choices=[
            ("PENDING", "Chờ thanh toán"),
            ("SUCCEEDED", "Thành công"),
            ("FAILED", "Không thành công"),
            ("REVIEW", "Cần kiểm tra hoàn tiền"),
        ],
    )
    payment_url = models.TextField()
    provider_transaction = models.CharField(max_length=100, unique=True, null=True)
    response_code = models.CharField(max_length=2, blank=True)
    bank_code = models.CharField(max_length=30, blank=True)
    promotion_code = models.CharField(max_length=100, blank=True)
    promotion_amount = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    review_reason = models.CharField(max_length=200, blank=True)
    transaction = models.OneToOneField(PaymentTransaction, null=True, on_delete=models.PROTECT)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(db_index=True)
    notified_at = models.DateTimeField(null=True)

    class Meta:
        ordering = ["-created_at", "-pk"]
        constraints = [
            models.CheckConstraint(condition=models.Q(amount__gt=0), name="vnpay_amount_positive")
        ]
