from decimal import Decimal
from django.contrib.auth.models import Group, Permission
from apps.accounts.models import User, RoleAssignment
from apps.stores.models import Store, Warehouse
from apps.products.models import Product, ProductVariant, Category, Brand
from apps.inventory.models import InventoryBalance, StockMovement


def scenario(quantity=10):
    admin = User.objects.create_superuser("admin@test.invalid", "Test-password-2026!")
    customer = User.objects.create_user("customer@test.invalid", "Test-password-2026!")
    other = User.objects.create_user("other@test.invalid", "Test-password-2026!")
    a = Store.objects.create(name="Test branch A")
    b = Store.objects.create(name="Test branch B")
    wa = Warehouse.objects.create(store=a, name="Test A")
    wb = Warehouse.objects.create(store=b, name="Test B")
    cat = Category.objects.create(name="Test category", source_key="test")
    brand = Brand.objects.create(name="Test brand")
    p = Product.objects.create(
        name="Test product",
        slug="test-product",
        category=cat,
        brand=brand,
        source_id="TEST",
        raw_specs="RAM: 16GB",
    )
    v = ProductVariant.objects.create(
        product=p, sku="TEST-SKU", price=Decimal("1234000"), condition="Test"
    )
    balance = InventoryBalance.objects.create(warehouse=wa, variant=v, on_hand=quantity)
    StockMovement.objects.create(
        balance=balance, delta=quantity, on_hand_after=quantity, kind="INITIAL", reference="fixture"
    )
    return {
        "admin": admin,
        "customer": customer,
        "other": other,
        "a": a,
        "b": b,
        "wa": wa,
        "wb": wb,
        "v": v,
        "p": p,
        "balance": balance,
    }


def assign(user, store, *codes):
    g = Group.objects.create(name="test-role-" + str(user.pk) + "-" + str(store.pk))
    g.permissions.set(
        Permission.objects.filter(content_type__app_label="accounts", codename__in=codes)
    )
    RoleAssignment.objects.create(user=user, store=store, group=g)


def checkout(s, **extra):
    return {
        "warehouse": s["wa"].pk,
        "channel": "ONLINE",
        "recipient_name": "Khách kiểm thử",
        "phone": "0901234567",
        "address": "Test address",
        "fulfillment": "DELIVERY",
        "payment_method": "COD",
        "items": [{"variant": s["v"].pk, "quantity": 1}],
        **extra,
    }
