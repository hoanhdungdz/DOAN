from rest_framework import serializers, viewsets
from rest_framework.response import Response
from rest_framework.exceptions import PermissionDenied
from common.filters import SearchMixin
from drf_spectacular.utils import extend_schema
from apps.accounts.permissions import store_ids
from apps.orders.models import Order
from .models import PaymentTransaction
from .services import record_payment


class PaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = PaymentTransaction
        fields = "__all__"


class PaymentInput(serializers.Serializer):
    order = serializers.IntegerField(min_value=1)
    kind = serializers.ChoiceField(choices=["CAPTURE", "REFUND"])
    reference = serializers.CharField(max_length=200, required=False, allow_blank=True, default="")


class PaymentViewSet(SearchMixin, viewsets.ReadOnlyModelViewSet):
    search_fields = ("reference", "kind", "order__code")
    queryset = PaymentTransaction.objects.all().order_by("-pk")
    serializer_class = PaymentSerializer

    def get_queryset(self):
        ids = store_ids(self.request.user, "manage_payments")
        if not ids:
            raise PermissionDenied()
        return self.queryset.filter(order__warehouse__store_id__in=ids)

    @extend_schema(request=PaymentInput, responses={201: PaymentSerializer})
    def create(self, request):
        s = PaymentInput(data=request.data)
        s.is_valid(raise_exception=True)
        d = s.validated_data
        if not Order.objects.filter(
            pk=d["order"], warehouse__store_id__in=store_ids(request.user, "manage_payments")
        ).exists():
            raise PermissionDenied()
        payment = record_payment(
            d["order"],
            request.user,
            d["kind"],
            request.headers.get("Idempotency-Key", ""),
            d["reference"],
        )
        return Response(self.get_serializer(payment).data, status=201)
