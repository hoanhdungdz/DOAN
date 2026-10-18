import uuid
from django.db import models
from django.conf import settings
from common.models import Timestamped


def order_code():
    return "TR" + uuid.uuid4().hex[:16].upper()


class Cart(Timestamped):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="cart"
    )


class CartItem(models.Model):
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name="items")
    variant = models.ForeignKey("products.ProductVariant", on_delete=models.PROTECT)
    quantity = models.PositiveIntegerField()

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["cart", "variant"], name="cart_variant"),
            models.CheckConstraint(
                condition=models.Q(quantity__gt=0), name="cart_positive_quantity"
            ),
        ]


class Order(Timestamped):
    code = models.CharField(max_length=30, unique=True, default=order_code)
    customer = models.ForeignKey("customers.Customer", on_delete=models.PROTECT)
    warehouse = models.ForeignKey("stores.Warehouse", on_delete=models.PROTECT)
    seller = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, on_delete=models.PROTECT, related_name="sales"
    )
    channel = models.CharField(max_length=15, default="ONLINE")
    status = models.CharField(max_length=15, default="PENDING")
    payment_method = models.CharField(max_length=20)
    payment_status = models.CharField(max_length=20, default="UNPAID")
    recipient_name = models.CharField(max_length=150)
    phone = models.CharField(max_length=30)
    address = models.CharField(max_length=500, blank=True)
    fulfillment = models.CharField(max_length=15, default="DELIVERY")
    subtotal = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    shipping_fee = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    grand_total = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    expires_at = models.DateTimeField(null=True)
    completed_at = models.DateTimeField(null=True, db_index=True)
    paid_at = models.DateTimeField(null=True)

    class Meta:
        indexes = [models.Index(fields=["warehouse", "status", "created_at"])]


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.PROTECT, related_name="items")
    variant = models.ForeignKey("products.ProductVariant", on_delete=models.PROTECT)
    name = models.CharField(max_length=500)
    sku = models.CharField(max_length=100)
    attributes = models.JSONField(default=dict)
    quantity = models.PositiveIntegerField()
    unit_price = models.DecimalField(max_digits=18, decimal_places=2)
    discount = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    line_total = models.DecimalField(max_digits=18, decimal_places=2)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=models.Q(quantity__gt=0), name="order_quantity_positive"
            )
        ]


class OrderStatusHistory(models.Model):
    order = models.ForeignKey(Order, on_delete=models.PROTECT, related_name="history")
    status = models.CharField(max_length=15)
    reason = models.CharField(max_length=500, blank=True)
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.PROTECT)
    created_at = models.DateTimeField(auto_now_add=True)


class Invoice(models.Model):
    order = models.OneToOneField(Order, on_delete=models.PROTECT, related_name="invoice")
    code = models.CharField(max_length=40, unique=True)
    snapshot = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)


class OTPChallenge(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    order = models.ForeignKey(Order, on_delete=models.PROTECT)
    code_hash = models.CharField(max_length=128)
    attempts = models.PositiveIntegerField(default=0)
    expires_at = models.DateTimeField()
    used_at = models.DateTimeField(null=True)
    created_at = models.DateTimeField(auto_now_add=True)
