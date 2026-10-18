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
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["order", "key"], name="payment_order_key"),
            models.CheckConstraint(
                condition=models.Q(amount__gt=0), name="payment_amount_positive"
            ),
        ]
