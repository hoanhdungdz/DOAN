from .models import AuditLog
from decimal import Decimal
from django.db import transaction

# Explicit allowlist: never serialize arbitrary input, passwords, tokens or chat.
AUDIT_FIELDS = {
    "name",
    "sku",
    "price",
    "condition",
    "warranty_months",
    "is_active",
    "email",
    "code",
    "title",
    "group",
    "store",
    "user",
    "permissions",
    "category",
    "brand",
    "warehouse",
}


def snapshot(instance, fields):
    if instance is None:
        return {}
    result = {}
    for key in fields:
        value = getattr(instance, key, None)
        if hasattr(value, "values_list"):
            value = list(value.values_list("pk", flat=True).order_by("pk"))
        elif hasattr(value, "pk"):
            value = value.pk
        elif isinstance(value, Decimal):
            value = str(value)
        result[key] = value
    return result


@transaction.atomic
def save_with_audit(actor, action, serializer, store=None, **extra):
    fields = AUDIT_FIELDS.intersection(serializer.validated_data)
    before = snapshot(serializer.instance, fields)
    obj = serializer.save(**extra)
    audit(actor, action, obj, store, before=before, after=snapshot(obj, fields))
    return obj


def audit(actor, action, obj, store=None, **changes):
    return AuditLog.objects.create(
        actor=actor if actor and actor.is_authenticated else None,
        store=store,
        action=action,
        object_type=obj._meta.label,
        object_id=str(obj.pk),
        changes=changes,
    )
