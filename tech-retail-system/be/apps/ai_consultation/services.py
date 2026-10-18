from abc import ABC, abstractmethod
from common.errors import BusinessError
from apps.products.models import ProductVariant
from apps.products.api import filter_catalog, VariantSerializer


class ConsultationProvider(ABC):
    @abstractmethod
    def consult(self, question, candidates):
        """Return structured candidate IDs/claims; never SQL or business operations."""


class DisabledProvider(ConsultationProvider):
    def consult(self, question, candidates):
        raise BusinessError("Chức năng tư vấn AI chưa được bật.", "AI_NOT_CONFIGURED", 503)


def retrieve(criteria, request=None, limit=12):
    qs = (
        ProductVariant.objects.filter(
            is_active=True,
            product__is_active=True,
            product__category__is_active=True,
            product__brand__is_active=True,
        )
        .select_related("product")
        .prefetch_related("product__images")
    )
    candidates = filter_catalog(qs, criteria, True)[: min(limit, 20)]
    return VariantSerializer(candidates, many=True, context={"request": request}).data
