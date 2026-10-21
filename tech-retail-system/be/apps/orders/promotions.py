"""Shop discounts are priced on the server, independently of provider promotions."""

from decimal import Decimal, ROUND_DOWN
from django.db.models import Q
from django.utils import timezone
from common.errors import BusinessError
from apps.products.models import ProductVariant
from .models import Coupon, CouponRedemption, Order


def active_redemptions(now=None):
    now = now or timezone.now()
    return CouponRedemption.objects.filter(
        Q(status="USED")
        | (
            Q(status="RESERVED")
            & ~Q(order__status="CANCELLED")
            & (
                ~Q(order__status="PENDING")
                | Q(order__expires_at__isnull=True)
                | Q(order__expires_at__gt=now)
            )
        )
    )


def basket_lines(items):
    variants = {
        v.pk: v
        for v in ProductVariant.objects.filter(
            pk__in=[r["variant"] for r in items],
            is_active=True,
            product__is_active=True,
            product__category__is_active=True,
            product__brand__is_active=True,
        ).select_related("product")
    }
    if len(variants) != len(items):
        raise BusinessError(
            "Sản phẩm không còn bán. Vui lòng kiểm tra giỏ hàng.", "VARIANT_UNAVAILABLE", 400
        )
    return [
        (variants[r["variant"]].product.category_id, variants[r["variant"]].price * r["quantity"])
        for r in items
    ]


def evaluate(coupon, user, lines, exclude_order=None):
    now = timezone.now()
    subtotal = sum((amount for _, amount in lines), Decimal("0"))
    categories = {category.pk for category in coupon.categories.all()}
    eligible = sum(
        (amount for category, amount in lines if not categories or category in categories),
        Decimal("0"),
    )
    uses = active_redemptions(now).filter(coupon=coupon)
    previous = (
        Order.objects.filter(customer__user=user)
        .exclude(pk=exclude_order)
        .exclude(
            Q(status="CANCELLED", payment_status="UNPAID")
            | Q(status="PENDING", payment_status="UNPAID", expires_at__lte=now)
        )
    )
    reason = ""
    if not coupon.is_active:
        reason = "Mã đã ngừng áp dụng."
    elif now < coupon.starts_at:
        reason = "Mã chưa đến thời gian áp dụng."
    elif now >= coupon.ends_at:
        reason = "Mã đã hết hạn."
    elif not user.is_authenticated:
        reason = "Vui lòng đăng nhập để dùng mã."
    elif eligible <= 0:
        reason = "Giỏ hàng chưa có sản phẩm thuộc danh mục áp dụng."
    elif eligible < coupon.min_subtotal:
        reason = f"Cần tiền hàng đủ điều kiện từ {vnd(coupon.min_subtotal)}."
    elif coupon.first_order_only and previous.exists():
        reason = "Mã chỉ dành cho đơn hàng đầu tiên."
    elif uses.count() >= coupon.usage_limit:
        reason = "Mã đã hết lượt sử dụng."
    elif uses.filter(user=user).count() >= coupon.per_user_limit:
        reason = "Bạn đã dùng hoặc đang giữ đủ lượt của mã này."
    amount = coupon.value if coupon.discount_type == "FIXED" else eligible * coupon.value / 100
    if coupon.max_discount is not None:
        amount = min(amount, coupon.max_discount)
    amount = min(amount, eligible).quantize(Decimal("1"), rounding=ROUND_DOWN)
    if not reason and (amount <= 0 or subtotal - amount < 1):
        reason = "Tổng tiền sau giảm cần còn ít nhất 1đ."
    return {
        "eligible": not reason,
        "reason": reason,
        "discount": str(amount if not reason else Decimal("0")),
    }


def vnd(value):
    return f"{int(value):,}".replace(",", ".") + "đ"


def coupon_card(coupon, result):
    categories = list(coupon.categories.all())
    benefit = (
        f"Giảm {vnd(coupon.value)}"
        if coupon.discount_type == "FIXED"
        else f"Giảm {coupon.value.normalize():f}%"
    )
    if coupon.discount_type == "PERCENT" and coupon.max_discount:
        benefit += f", tối đa {vnd(coupon.max_discount)}"
    scope = ", ".join(c.name for c in categories) if categories else "Tiền hàng"
    return {
        "code": coupon.code,
        "name": coupon.name,
        "benefit": benefit,
        "condition": f"{scope} từ {vnd(coupon.min_subtotal)}",
        "first_order_only": coupon.first_order_only,
        "per_user_limit": coupon.per_user_limit,
        "ends_at": coupon.ends_at.isoformat(),
        **result,
    }


def preview(items, user, code=""):
    lines = basket_lines(items)
    subtotal = sum((amount for _, amount in lines), Decimal("0"))
    cards, applied, error = [], None, ""
    for coupon in Coupon.objects.filter(is_active=True).prefetch_related("categories"):
        card = coupon_card(coupon, evaluate(coupon, user, lines))
        cards.append(card)
        if coupon.code == code:
            if card["eligible"]:
                applied = card
            else:
                error = card["reason"]
    if code and not applied and not error:
        error = "Mã không tồn tại hoặc đã ngừng áp dụng."
    discount = Decimal(applied["discount"]) if applied else Decimal("0")
    return {
        "coupons": cards,
        "applied_coupon": applied,
        "coupon_error": error,
        "subtotal": str(subtotal),
        "discount_total": str(discount),
        "shipping_fee": "0",
        "grand_total": str(subtotal - discount),
    }


def reserve_coupon(order, user, lines, code):
    # Caller holds the customer account and variant locks. Global coupon lock
    # serializes capacity checks across customers and warehouses.
    coupon = Coupon.objects.select_for_update().filter(code=code).first()
    if not coupon:
        raise BusinessError("Mã không tồn tại hoặc đã ngừng áp dụng.", "COUPON_INVALID", 400)
    result = evaluate(coupon, user, lines, exclude_order=order.pk)
    if not result["eligible"]:
        raise BusinessError(result["reason"], "COUPON_INVALID", 400)
    order.discount_total = Decimal(result["discount"])
    order.coupon_code = coupon.code
    order.coupon_snapshot = {
        "code": coupon.code,
        "name": coupon.name,
        "discount_type": coupon.discount_type,
        "value": str(coupon.value),
        "max_discount": str(coupon.max_discount) if coupon.max_discount is not None else None,
        "categories": list(coupon.categories.values_list("id", flat=True)),
    }
    CouponRedemption.objects.create(coupon=coupon, user=user, order=order)


def use_coupon(order):
    CouponRedemption.objects.filter(order=order, status="RESERVED").update(status="USED")


def release_coupon(order):
    CouponRedemption.objects.filter(order=order, status="RESERVED").update(status="RELEASED")
