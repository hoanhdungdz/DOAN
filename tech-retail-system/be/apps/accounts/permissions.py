from rest_framework.exceptions import PermissionDenied
from .models import RoleAssignment


def is_admin(user):
    return user.is_authenticated and user.is_active and user.is_superuser


def store_ids(user, capability=None):
    from apps.stores.models import Store

    if not user.is_authenticated or not user.is_active:
        return []
    if is_admin(user):
        return list(Store.objects.values_list("id", flat=True))
    qs = RoleAssignment.objects.filter(user=user)
    if capability:
        qs = qs.filter(
            group__permissions__codename=capability,
            group__permissions__content_type__app_label="accounts",
        )
    return list(qs.values_list("store_id", flat=True).distinct())


def require(user, capability, store=None):
    if is_admin(user):
        return
    if (
        capability == "manage_accounts"
        or store is None
        or int(store.pk if hasattr(store, "pk") else store) not in store_ids(user, capability)
    ):
        raise PermissionDenied("Bạn không có quyền thực hiện tại chi nhánh này.")


def capabilities(user):
    if is_admin(user):
        return [
            "manage_accounts",
            "manage_sales",
            "manage_payments",
            "manage_stock",
            "view_reports",
            "view_audit",
            "manage_people",
        ]
    if not user.is_authenticated:
        return []
    return list(
        RoleAssignment.objects.filter(user=user)
        .values_list("group__permissions__codename", flat=True)
        .distinct()
    )
