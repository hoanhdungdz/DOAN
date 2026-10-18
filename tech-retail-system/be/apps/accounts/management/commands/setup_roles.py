from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group, Permission


class Command(BaseCommand):
    help = "Create default RBAC groups. Does not create accounts or overwrite existing grants."

    def handle(self, *a, **o):
        roles = {
            "Store Manager": [
                "manage_sales",
                "manage_payments",
                "manage_stock",
                "view_reports",
                "view_audit",
                "manage_people",
            ],
            "Sales Staff": ["manage_sales", "manage_payments"],
            "Warehouse Staff": ["manage_stock"],
            "Customer": [],
        }
        for name, codes in roles.items():
            group, created = Group.objects.get_or_create(name=name)
            if created:
                group.permissions.set(
                    Permission.objects.filter(
                        content_type__app_label="accounts", codename__in=codes
                    )
                )
        self.stdout.write(
            "Default groups ready. Admin uses is_superuser; no default account created."
        )
