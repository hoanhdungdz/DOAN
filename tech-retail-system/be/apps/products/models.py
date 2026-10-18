from django.db import models
from common.models import Timestamped


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
