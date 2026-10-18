import json
from django.core.management.base import BaseCommand
from apps.products.quality import review_master_catalog


class Command(BaseCommand):
    help = "Preview reviewed metadata corrections; --apply records audits without merging stock."

    def add_arguments(self, parser):
        parser.add_argument("--apply", action="store_true")

    def handle(self, *args, **options):
        self.stdout.write(
            json.dumps(
                review_master_catalog(dry_run=not options["apply"]), ensure_ascii=False, indent=2
            )
        )
