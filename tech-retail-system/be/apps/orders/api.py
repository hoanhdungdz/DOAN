import re
from django.db import transaction
from django.db.models import Q
from rest_framework import serializers, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from drf_spectacular.utils import extend_schema, extend_schema_view, extend_schema_field
from apps.accounts.permissions import store_ids
from apps.products.models import ProductVariant
from apps.products.api import VariantSerializer
from .models import Order, OrderItem, OrderStatusHistory, Cart, CartItem, Invoice
from .services import create_order, transition_order, finish_pos, expire_orders
from apps.stores.models import Warehouse
from common.filters import SearchMixin


def normalize_phone(value):
    phone = re.sub(r"[\s.()+-]", "", value)
    if not re.fullmatch(r"\d{9,15}", phone):
        raise serializers.ValidationError("Số điện thoại cần 9–15 chữ số.")
    return phone


class CheckoutItem(serializers.Serializer):
    variant = serializers.IntegerField(min_value=1)
    quantity = serializers.IntegerField(min_value=1, max_value=1000)


class CheckoutSerializer(serializers.Serializer):
    warehouse = serializers.IntegerField(min_value=1)
    channel = serializers.ChoiceField(choices=["ONLINE", "IN_STORE"], default="ONLINE")
    customer = serializers.IntegerField(min_value=1, required=False, allow_null=True)
    recipient_name = serializers.CharField(max_length=150)
    phone = serializers.CharField(max_length=30)
    address = serializers.CharField(max_length=500, required=False, allow_blank=True, default="")
    fulfillment = serializers.ChoiceField(choices=["DELIVERY", "PICKUP"])
    payment_method = serializers.ChoiceField(
        choices=["COD", "CASH", "BANK_TRANSFER", "VNPAY_SANDBOX"]
    )
    items = CheckoutItem(many=True)
    coupon_code = serializers.CharField(max_length=32, required=False, allow_blank=True, default="")
    quoted_total = serializers.DecimalField(
        max_digits=18, decimal_places=2, min_value=0, required=False
    )

    def validate_coupon_code(self, value):
        return value.strip().upper()

    def validate_phone(self, value):
        return normalize_phone(value)

    def validate(self, data):
        if data["channel"] == "ONLINE" and data.get("customer"):
            raise serializers.ValidationError(
                {
                    "customer": "Đơn online lấy khách hàng từ phiên đăng nhập; không tự chọn hồ sơ khác."
                }
            )
        if data["fulfillment"] == "DELIVERY" and not data["address"].strip():
            raise serializers.ValidationError({"address": "Cần địa chỉ giao hàng."})
        rows = data["items"]
        if not rows or len(rows) > 100 or len({r["variant"] for r in rows}) != len(rows):
            raise serializers.ValidationError({"items": "Cần 1–100 dòng hàng không trùng."})
        return data


class OrderItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderItem
        fields = "__all__"


class HistorySerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderStatusHistory
        fields = "__all__"


class OrderSerializer(serializers.ModelSerializer):
    vnpay_payment = serializers.SerializerMethodField()
    items = OrderItemSerializer(many=True, read_only=True)
    history = HistorySerializer(many=True, read_only=True)
    store_name = serializers.CharField(source="warehouse.store.name", read_only=True)
    store = serializers.IntegerField(source="warehouse.store_id", read_only=True)

    @extend_schema_field({"type": "object", "nullable": True, "additionalProperties": True})
    def get_vnpay_payment(self, obj):
        from apps.payments.vnpay import public_attempt

        attempts = list(obj.vnpay_attempts.all())
        relevant = next(
            (a for a in attempts if a.status == "REVIEW"), attempts[0] if attempts else None
        )
        return public_attempt(relevant) if relevant else None

    class Meta:
        model = Order
        fields = "__all__"


class OrderViewSet(viewsets.GenericViewSet):
    permission_classes = [IsAuthenticated]
    queryset = (
        Order.objects.select_related("customer", "warehouse__store")
        .prefetch_related("items", "history", "vnpay_attempts")
        .all()
        .order_by("-pk")
    )
    serializer_class = OrderSerializer

    def get_queryset(self):
        user = self.request.user
        if not user.is_authenticated:
            raise PermissionDenied("Đăng nhập để xem đơn hàng của bạn.")
        ids = (
            store_ids(user, "manage_sales")
            + store_ids(user, "manage_payments")
            + store_ids(user, "manage_people")
        )
        qs = self.queryset.filter(
            Q(customer__user=user) | Q(warehouse__store_id__in=ids)
        ).distinct()
        if self.request.query_params.get("status"):
            qs = qs.filter(status=self.request.query_params["status"])
        if self.request.query_params.get("search"):
            qs = qs.filter(code__icontains=self.request.query_params["search"])
        if self.request.query_params.get("store"):
            qs = qs.filter(warehouse__store_id=self.request.query_params["store"])
        if self.request.query_params.get("customer"):
            qs = qs.filter(customer_id=self.request.query_params["customer"])
        return qs

    def list(self, request):
        return self.get_paginated_response(
            self.get_serializer(self.paginate_queryset(self.get_queryset()), many=True).data
        )

    def retrieve(self, request, pk=None):
        return Response(self.get_serializer(self.get_object()).data)

    @extend_schema(request=CheckoutSerializer, responses={201: OrderSerializer})
    def create(self, request):
        s = CheckoutSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        if not request.session.session_key:
            request.session.create()
        scope = (
            "user:" + str(request.user.pk)
            if request.user.is_authenticated
            else "session:" + request.session.session_key
        )
        order = create_order(
            s.validated_data, request.user, scope, request.headers.get("Idempotency-Key", "")
        )
        return Response(self.get_serializer(order).data, status=201)

    def do(self, request, action):
        obj = self.get_object()
        reason = request.data.get("reason", "")
        if not isinstance(reason, str) or len(reason) > 500:
            raise serializers.ValidationError({"reason": "Lý do quá dài hoặc không hợp lệ."})
        return Response(
            self.get_serializer(transition_order(obj.pk, action, request.user, reason)).data
        )

    @action(detail=True, methods=["post"])
    def confirm(self, request, pk=None):
        return self.do(request, "confirm")

    @action(detail=True, methods=["post"])
    def pack(self, request, pk=None):
        return self.do(request, "pack")

    @action(detail=True, methods=["post"])
    def ship(self, request, pk=None):
        return self.do(request, "ship")

    @action(detail=True, methods=["post"])
    def complete(self, request, pk=None):
        return self.do(request, "complete")

    @action(detail=True, methods=["post"])
    def cancel(self, request, pk=None):
        return self.do(request, "cancel")

    @action(detail=True, methods=["post"])
    def finish(self, request, pk=None):
        obj = self.get_object()
        reference = request.data.get("reference", "")
        if not isinstance(reference, str) or len(reference) > 200:
            raise serializers.ValidationError({"reference": "Tham chiếu không hợp lệ."})
        return Response(
            self.get_serializer(
                finish_pos(
                    obj.pk, request.user, request.headers.get("Idempotency-Key", ""), reference
                )
            ).data
        )


class CancelOwnOrderInput(serializers.Serializer):
    reason = serializers.CharField(max_length=500)


class MyOrderViewSet(SearchMixin, viewsets.ReadOnlyModelViewSet):
    """Personal order history never inherits an employee's branch permissions."""

    permission_classes = [IsAuthenticated]
    serializer_class = OrderSerializer
    queryset = OrderViewSet.queryset
    search_fields = ("code",)

    def get_queryset(self):
        return self.queryset.filter(customer__user=self.request.user)

    @extend_schema(request=CancelOwnOrderInput, responses=OrderSerializer)
    @action(detail=True, methods=["post"])
    def cancel(self, request, pk=None):
        order = self.get_object()
        data = CancelOwnOrderInput(data=request.data)
        data.is_valid(raise_exception=True)
        result = transition_order(order.pk, "cancel", request.user, data.validated_data["reason"])
        return Response(self.get_serializer(result).data)


class CartInputSerializer(serializers.Serializer):
    items = CheckoutItem(many=True)


class CartResponseSerializer(serializers.Serializer):
    items = serializers.ListField(child=serializers.DictField())
    warnings = serializers.ListField(child=serializers.CharField())


class CartAvailabilityView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(request=CartInputSerializer, responses=CartResponseSerializer)
    def post(self, request):
        data = CartInputSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        rows = data.validated_data["items"]
        if not rows or len(rows) > 100 or len({row["variant"] for row in rows}) != len(rows):
            raise serializers.ValidationError("Cần 1–100 dòng hàng không trùng.")
        # Refresh is a CSRF-protected POST: release expired holds in relevant active
        # warehouses before deciding which branches can fulfill this basket.
        warehouses = list(
            Warehouse.objects.filter(
                is_active=True,
                store__is_active=True,
                balances__variant_id__in=[row["variant"] for row in rows],
            )
            .values_list("id", flat=True)
            .distinct()
        )
        expire_orders(warehouses)
        variants = (
            ProductVariant.objects.filter(
                pk__in=[row["variant"] for row in rows],
                is_active=True,
                product__is_active=True,
                product__category__is_active=True,
                product__brand__is_active=True,
            )
            .select_related("product")
            .prefetch_related("product__images")
        )
        details = {
            variant.pk: VariantSerializer(variant, context={"request": request}).data
            for variant in variants
        }
        return Response(
            {
                "items": [{**row, "details": details.get(row["variant"])} for row in rows],
                "warnings": [],
            }
        )


@extend_schema_view(
    get=extend_schema(responses=CartResponseSerializer),
    put=extend_schema(request=CartInputSerializer, responses=CartResponseSerializer),
    post=extend_schema(request=CartInputSerializer, responses=CartResponseSerializer),
    delete=extend_schema(responses=CartResponseSerializer),
)
class CartView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        cart, _ = Cart.objects.get_or_create(user=request.user)
        rows = []
        warnings = []
        for item in cart.items.select_related("variant__product"):
            details = VariantSerializer(item.variant, context={"request": request}).data
            available = sum(s["available"] for s in details["stock"])
            if item.quantity > available:
                warnings.append(
                    f"{item.variant.sku}: giỏ có {item.quantity}, tổng khả dụng hiện tại {available}; cần kiểm tra chi nhánh trước checkout."
                )
            rows.append({"variant": item.variant_id, "quantity": item.quantity, "details": details})
        return Response({"items": rows, "warnings": warnings})

    def put(self, request):
        return self.save(request, False)

    def post(self, request):
        return self.save(request, True)

    def save(self, request, merge):
        s = CheckoutItem(data=request.data.get("items", []), many=True)
        s.is_valid(raise_exception=True)
        rows = s.validated_data
        skipped = []
        if len(rows) > 100 or len({r["variant"] for r in rows}) != len(rows):
            raise serializers.ValidationError("Tối đa 100 dòng không trùng.")
        with transaction.atomic():
            cart, _ = Cart.objects.get_or_create(user=request.user)
            cart = Cart.objects.select_for_update().get(pk=cart.pk)
            if not merge:
                cart.items.all().delete()
            for row in rows:
                v = ProductVariant.objects.filter(
                    pk=row["variant"],
                    is_active=True,
                    product__is_active=True,
                    product__category__is_active=True,
                    product__brand__is_active=True,
                ).first()
                if not v:
                    if merge:
                        skipped.append(
                            "Một sản phẩm trong giỏ cũ đã ngừng bán hoặc không còn tồn tại; sản phẩm này không được gộp."
                        )
                        continue
                    raise serializers.ValidationError("Sản phẩm không còn bán.")
                item, created = CartItem.objects.get_or_create(
                    cart=cart, variant=v, defaults={"quantity": row["quantity"]}
                )
                if merge and not created:
                    item.quantity += row["quantity"]
                    if item.quantity > 1000:
                        raise serializers.ValidationError(
                            "Tối đa 1000 đơn vị mỗi sản phẩm trong giỏ."
                        )
                    item.save(update_fields=["quantity"])
        response = self.get(request)
        response.data["warnings"] = skipped + response.data["warnings"]
        return response

    def delete(self, request):
        CartItem.objects.filter(
            cart__user=request.user, variant_id=request.query_params.get("variant")
        ).delete()
        return self.get(request)


class InvoiceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Invoice
        fields = "__all__"


class InvoiceViewSet(SearchMixin, viewsets.ReadOnlyModelViewSet):
    search_fields = ("code", "order__code")
    queryset = Invoice.objects.select_related("order").all().order_by("-pk")
    serializer_class = InvoiceSerializer

    def get_queryset(self):
        if not self.request.user.is_authenticated:
            raise PermissionDenied()
        ids = store_ids(self.request.user, "manage_sales") + store_ids(
            self.request.user, "manage_payments"
        )
        return self.queryset.filter(
            Q(order__customer__user=self.request.user) | Q(order__warehouse__store_id__in=ids)
        ).distinct()
