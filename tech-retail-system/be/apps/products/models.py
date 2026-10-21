from django.db import models
from common.models import Timestamped
from django.conf import settings


class Category(models.Model):
    name = models.CharField(max_length=150, unique=True)
    source_key = models.CharField(max_length=100, unique=True)
    is_active = models.BooleanField(default=True)


class Brand(models.Model):
    name = models.CharField(max_length=150, unique=True)
    is_active = models.BooleanField(default=True)


class Product(Timestamped):
    name = models.CharField(max_length=500)
    slug = models.SlugField(max_length=250, unique=True)
    category = models.ForeignKey(Category, on_delete=models.PROTECT)
    brand = models.ForeignKey(Brand, on_delete=models.PROTECT)
    description = models.TextField(blank=True)
    raw_specs = models.TextField(blank=True)
    source_namespace = models.CharField(max_length=60, default="master_dataset")
    source_id = models.CharField(max_length=80)
    original_slug = models.CharField(max_length=500, blank=True)
    source_url = models.URLField(max_length=1000, blank=True)
    source_snapshot = models.JSONField(default=dict)
    is_active = models.BooleanField(default=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["source_namespace", "source_id"], name="product_source_identity"
            )
        ]


class ProductVariant(Timestamped):
    product = models.ForeignKey(Product, on_delete=models.PROTECT, related_name="variants")
    sku = models.CharField(max_length=100, unique=True)
    name = models.CharField(max_length=200, default="Mặc định")
    price = models.DecimalField(max_digits=18, decimal_places=2)
    condition = models.CharField(max_length=100)
    warranty_months = models.PositiveIntegerField(default=0)
    attributes = models.JSONField(default=dict)
    is_active = models.BooleanField(default=True)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=models.Q(price__gte=0), name="variant_price_nonnegative"
            )
        ]


class ProductImage(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="images")
    url = models.URLField(max_length=1500)
    display_order = models.PositiveIntegerField(default=0)


class SpecificationDefinition(models.Model):
    name = models.CharField(max_length=200, unique=True)


class ProductSpecification(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="specifications")
    definition = models.ForeignKey(SpecificationDefinition, on_delete=models.PROTECT)
    value = models.TextField()
    numeric_value = models.DecimalField(max_digits=18, decimal_places=4, null=True)
    unit = models.CharField(max_length=30, blank=True)

    class Meta:
        indexes = [models.Index(fields=["definition", "numeric_value"])]


class ProductFeedback(Timestamped):
    product = models.ForeignKey(Product, on_delete=models.PROTECT, related_name="feedback")
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    kind = models.CharField(
        max_length=10, choices=[("REVIEW", "Đánh giá"), ("QUESTION", "Hỏi đáp")]
    )
    title = models.CharField(max_length=150, blank=True)
    body = models.CharField(max_length=3000)
    rating = models.PositiveSmallIntegerField(null=True)
    verified_order = models.ForeignKey("orders.Order", null=True, on_delete=models.PROTECT)
    # NULL for questions; one review per customer/product enforced also under concurrency.
    review_identity = models.CharField(max_length=80, null=True, unique=True)
    status = models.CharField(
        max_length=10,
        default="PENDING",
        choices=[("PENDING", "Chờ duyệt"), ("APPROVED", "Đã duyệt"), ("HIDDEN", "Đã ẩn")],
    )

    class Meta:
        ordering = ["-created_at", "-id"]
        indexes = [models.Index(fields=["product", "kind", "status", "created_at"])]
        constraints = [
            models.CheckConstraint(
                condition=(
                    models.Q(
                        kind="REVIEW",
                        rating__isnull=False,
                        rating__gte=1,
                        rating__lte=5,
                        verified_order__isnull=False,
                        review_identity__isnull=False,
                    )
                    | models.Q(
                        kind="QUESTION",
                        rating__isnull=True,
                        verified_order__isnull=True,
                        review_identity__isnull=True,
                    )
                ),
                name="feedback_valid_review_or_question",
            )
        ]


class FeedbackPhoto(models.Model):
    feedback = models.ForeignKey(ProductFeedback, on_delete=models.CASCADE, related_name="photos")
    content = models.BinaryField()


class FeedbackReply(Timestamped):
    feedback = models.ForeignKey(ProductFeedback, on_delete=models.PROTECT, related_name="replies")
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    body = models.CharField(max_length=3000)
    is_staff_reply = models.BooleanField(default=False)
    status = models.CharField(
        max_length=10,
        default="PENDING",
        choices=[("PENDING", "Chờ duyệt"), ("APPROVED", "Đã duyệt"), ("HIDDEN", "Đã ẩn")],
    )

    class Meta:
        ordering = ["created_at", "id"]


class FeedbackVote(models.Model):
    feedback = models.ForeignKey(ProductFeedback, on_delete=models.CASCADE, related_name="votes")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["feedback", "user"], name="feedback_vote_once")
        ]


class FeedbackReport(Timestamped):
    feedback = models.ForeignKey(ProductFeedback, on_delete=models.PROTECT, related_name="reports")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    reason = models.CharField(max_length=500)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["feedback", "user"], name="feedback_report_once")
        ]
