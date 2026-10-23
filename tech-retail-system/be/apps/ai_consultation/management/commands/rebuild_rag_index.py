from django.core.management.base import BaseCommand, CommandError
import time
from common.errors import BusinessError
from apps.ai_consultation.index import documents, sync_index
from apps.ai_consultation.provider import GeminiProvider, ready


class Command(BaseCommand):
    help = "Index public catalog/policies for RAG; never writes business database or chat history."

    def add_arguments(self, parser):
        parser.add_argument("--rebuild", action="store_true", help="Re-embed all documents.")

    def handle(self, *args, **options):
        if not ready():
            raise CommandError("Configure GEMINI_ENABLED and GEMINI_API_KEY in the backend.")
        try:
            provider = GeminiProvider()
            # CLI-only bounded wait. Web chat fails promptly on quota instead of hanging.
            embed = provider.embed

            def with_quota_wait(texts, **kwargs):
                for attempt in range(3):
                    try:
                        return embed(texts, **kwargs)
                    except BusinessError as exc:
                        if exc.detail.code != "AI_QUOTA_EXCEEDED" or attempt == 2:
                            raise
                        self.stdout.write(
                            "Embedding quota pause: 40 seconds; successful batches are saved."
                        )
                        time.sleep(40)

            provider.embed = with_quota_wait
            rows, changed = sync_index(
                documents(),
                provider,
                rebuild=options["rebuild"],
                progress=lambda done, total: self.stdout.write(
                    f"Embedded {done}/{total} changed chunks."
                ),
            )
        except BusinessError as exc:
            raise CommandError(str(exc.detail)) from None
        self.stdout.write(
            self.style.SUCCESS(f"RAG index ready: {len(rows)} chunks, {changed} refreshed.")
        )
