import json
from django.core.management.base import BaseCommand, CommandError
from django.db.models import Sum
from apps.inventory.models import InventoryBalance


class Command(BaseCommand):
    help = "Read-only reconciliation of balances versus stock and reservation ledgers."

    def handle(self, *a, **o):
        errors = []
        for b in InventoryBalance.objects.all():
            total = b.movements.aggregate(n=Sum("delta"))["n"] or 0
            reserved = b.reservations.filter(status="ACTIVE").aggregate(n=Sum("quantity"))["n"] or 0
            if total != b.on_hand or reserved != b.reserved:
                errors.append(
                    {
                        "balance": b.pk,
                        "ledger": total,
                        "on_hand": b.on_hand,
                        "active_reservations": reserved,
                        "reserved": b.reserved,
                    }
                )
        self.stdout.write(
            json.dumps({"checked": InventoryBalance.objects.count(), "mismatches": errors})
        )
        if errors:
            raise CommandError("Inventory reconciliation failed")
