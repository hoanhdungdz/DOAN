import json
from django.core.management.base import BaseCommand, CommandError
from apps.products.importer import import_dataset
from common.errors import BusinessError


class Command(BaseCommand):
    help = "Validate/import the complete master dataset atomically; safe to rerun."

    def add_arguments(self, p):
        p.add_argument("--file", required=True)
        p.add_argument("--dry-run", action="store_true")

    def handle(self, *args, **o):
        try:
            result = import_dataset(o["file"], o["dry_run"])
        except (BusinessError, ValueError, OSError) as exc:
            raise CommandError(str(exc)) from exc
        self.stdout.write(json.dumps(result, ensure_ascii=False, indent=2))
