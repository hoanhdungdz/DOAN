from datetime import timedelta
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone
from apps.orders.models import Coupon
from apps.products.models import Category


class Command(BaseCommand):
    help = "Create three shop demo coupons without overwriting existing promotions."

    @transaction.atomic
    def handle(self, *args, **options):
        accessories = Category.objects.filter(source_key="Phu_kien_Cong_nghe").first()
        if not accessories:
            raise CommandError(
                "Import catalog category Phu_kien_Cong_nghe first; accessory coupon must never apply to all products."
            )
        now = timezone.now()
        common = {
            "starts_at": now,
            "ends_at": now + timedelta(days=30),
            "usage_limit": 1000,
            "per_user_limit": 1,
        }
        samples = [
            (
                "TECH100K",
                {
                    "name": "Giảm 100.000đ cho đơn từ 5 triệu",
                    "discount_type": "FIXED",
                    "value": 100000,
                    "min_subtotal": 5000000,
                },
            ),
            (
                "CHAO5",
                {
                    "name": "Chào khách mới: giảm 5%",
                    "discount_type": "PERCENT",
                    "value": 5,
                    "min_subtotal": 1000000,
                    "max_discount": 200000,
                    "first_order_only": True,
                },
            ),
            (
                "PHUKIEN50K",
                {
                    "name": "Giảm 50.000đ cho phụ kiện",
                    "discount_type": "FIXED",
                    "value": 50000,
                    "min_subtotal": 500000,
                },
            ),
        ]
        for code, defaults in samples:
            coupon, created = Coupon.objects.get_or_create(
                code=code, defaults={**common, **defaults}
            )
            if created and code == "PHUKIEN50K":
                coupon.categories.set([accessories])
            self.stdout.write(f"{code}: {'created' if created else 'kept existing'}")
