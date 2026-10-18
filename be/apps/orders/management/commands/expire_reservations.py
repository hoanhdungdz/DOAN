from django.core.management.base import BaseCommand
from apps.orders.services import expire_orders


class Command(BaseCommand):
    help = "Cancel expired PENDING orders and release their reservations exactly once."

    def handle(self, *a, **o):
        self.stdout.write(str(expire_orders()))
