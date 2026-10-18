from django.db.models import Q


class SearchMixin:
    search_fields = ()

    def filter_queryset(self, queryset):
        queryset = super().filter_queryset(queryset)
        search = self.request.query_params.get("search", "").strip()[:200]
        if search and self.search_fields:
            query = Q()
            for field in self.search_fields:
                query |= Q(**{field + "__icontains": search})
            queryset = queryset.filter(query).distinct()
        return queryset
