from django.db import models
from common.models import Timestamped


class Store(Timestamped):
    name = models.CharField(max_length=200, unique=True)
    address = models.CharField(max_length=500, blank=True)
    phone = models.CharField(max_length=30, blank=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.name


class Warehouse(Timestamped):
    store = models.ForeignKey(Store, on_delete=models.PROTECT, related_name="warehouses")
    name = models.CharField(max_length=200)
    is_active = models.BooleanField(default=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["store", "name"], name="warehouse_store_name")
        ]
