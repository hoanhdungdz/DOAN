from apps.products.models import ProductVariant
from apps.products.api import filter_catalog, VariantSerializer


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
