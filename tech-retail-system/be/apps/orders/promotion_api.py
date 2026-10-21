import re
from decimal import Decimal
from django.db import transaction
from rest_framework import serializers, mixins, viewsets
from rest_framework.permissions import BasePermission, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from drf_spectacular.utils import extend_schema
from apps.accounts.permissions import is_admin
from common.audit import audit
from common.filters import SearchMixin
from .api import CheckoutItem
from .models import Coupon
from .promotions import preview, active_redemptions


class AdminOnly(BasePermission):
    def has_permission(self, request, view):
        return is_admin(request.user)


class CouponSerializer(serializers.ModelSerializer):
    reserved_count = serializers.SerializerMethodField()
    used_count = serializers.SerializerMethodField()

    def get_reserved_count(self, obj) -> int:
        return active_redemptions().filter(coupon=obj, status="RESERVED").count()

    def get_used_count(self, obj) -> int:
        return obj.redemptions.filter(status="USED").count()

    def validate_code(self, value):
        value = value.strip().upper()
        if not re.fullmatch(r"[A-Z0-9][A-Z0-9_-]{2,31}", value):
            raise serializers.ValidationError(
                "Mã cần 3–32 ký tự chữ, số, dấu gạch ngang hoặc gạch dưới."
            )
        if self.instance and value != self.instance.code:
            raise serializers.ValidationError("Không đổi mã đã tạo; hãy tạo mã mới.")
        return value

    def validate(self, attrs):
        def value(name, default=None):
            return attrs.get(name, getattr(self.instance, name, default))

        amount = value("value")
        cap = value("max_discount")
        if amount is not None and (
            amount <= 0
            or (value("discount_type") == "FIXED" and amount != amount.to_integral_value())
        ):
            raise serializers.ValidationError(
                {"value": "Mức giảm phải dương; số tiền giảm cần là số nguyên VND."}
            )
        if value("discount_type") == "PERCENT" and (amount > 100 or cap is None):
            raise serializers.ValidationError(
                {"max_discount": "Giảm phần trăm cần mức tối đa; tỷ lệ không vượt 100%."}
            )
        if cap is not None and (cap < 1 or cap != cap.to_integral_value()):
            raise serializers.ValidationError(
                {"max_discount": "Mức giảm tối đa cần là số nguyên VND dương."}
            )
        if value("min_subtotal", Decimal("0")) < 0:
            raise serializers.ValidationError(
                {"min_subtotal": "Giá trị đơn tối thiểu không được âm."}
            )
        if value("per_user_limit", 1) < 1 or value("usage_limit", 100) < 1:
            raise serializers.ValidationError("Giới hạn lượt phải lớn hơn 0.")
        if value("starts_at") and value("ends_at") and value("starts_at") >= value("ends_at"):
            raise serializers.ValidationError(
                {"ends_at": "Thời gian kết thúc phải sau thời gian bắt đầu."}
            )
        return attrs

    class Meta:
        model = Coupon
        fields = "__all__"
        read_only_fields = ["created_at", "updated_at"]


class CouponViewSet(
    SearchMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.CreateModelMixin,
    mixins.UpdateModelMixin,
    viewsets.GenericViewSet,
):
    permission_classes = [IsAuthenticated, AdminOnly]
    serializer_class = CouponSerializer
    queryset = Coupon.objects.prefetch_related("categories").all()
    search_fields = ("code", "name")

    def perform_create(self, serializer):
        with transaction.atomic():
            coupon = serializer.save()
            audit(self.request.user, "coupon.create", coupon)

    def update(self, request, *args, **kwargs):
        with transaction.atomic():
            # Same lock as checkout: edits cannot race its eligibility check.
            Coupon.objects.select_for_update().get(pk=self.get_object().pk)
            response = super().update(request, *args, **kwargs)
            audit(request.user, "coupon.update", self.get_object())
            return response


class PromotionPreviewInput(serializers.Serializer):
    items = CheckoutItem(many=True)
    coupon_code = serializers.CharField(max_length=32, required=False, allow_blank=True, default="")

    def validate_items(self, rows):
        if not rows or len(rows) > 100 or len({r["variant"] for r in rows}) != len(rows):
            raise serializers.ValidationError("Cần 1–100 dòng hàng không trùng.")
        return rows


class PromotionPreviewView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        request=PromotionPreviewInput,
        responses={200: {"type": "object", "additionalProperties": True}},
    )
    def post(self, request):
        data = PromotionPreviewInput(data=request.data)
        data.is_valid(raise_exception=True)
        return Response(
            preview(
                data.validated_data["items"],
                request.user,
                data.validated_data["coupon_code"].strip().upper(),
            )
        )
