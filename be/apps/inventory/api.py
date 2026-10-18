from django.db import transaction
from django.db.models import Q, F
from rest_framework import serializers, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response
from common.errors import BusinessError
from common.audit import audit
from common.filters import SearchMixin
from apps.accounts.permissions import store_ids, require
from apps.products.models import ProductVariant
from .models import (
    InventoryBalance,
    StockMovement,
    InventoryReservation,
    StockDocument,
    StockDocumentItem,
    StockTransfer,
    StockTransferItem,
)
from .services import post_document, transition_transfer, lock_warehouses


class ItemInput(serializers.Serializer):
    variant = serializers.PrimaryKeyRelatedField(queryset=ProductVariant.objects.all())
    sku = serializers.CharField(source="variant.sku", read_only=True)
    name = serializers.CharField(source="variant.product.name", read_only=True)
    quantity = serializers.IntegerField(min_value=-100000, max_value=100000)


class BalanceSerializer(serializers.ModelSerializer):
    available = serializers.IntegerField(read_only=True)
    sku = serializers.CharField(source="variant.sku", read_only=True)
    product_name = serializers.CharField(source="variant.product.name", read_only=True)
    store = serializers.IntegerField(source="warehouse.store_id", read_only=True)
    warehouse_name = serializers.CharField(source="warehouse.name", read_only=True)

    class Meta:
        model = InventoryBalance
        fields = "__all__"


class BalanceViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = BalanceSerializer
    queryset = (
        InventoryBalance.objects.select_related("warehouse", "variant__product")
        .all()
        .order_by("warehouse_id", "variant_id")
    )

    def get_queryset(self):
        ids = set(
            store_ids(self.request.user, "manage_stock")
            + store_ids(self.request.user, "manage_sales")
            + store_ids(self.request.user, "view_reports")
        )
        if not ids:
            raise PermissionDenied()
        qs = self.queryset.filter(warehouse__store_id__in=ids)
        p = self.request.query_params
        if p.get("warehouse"):
            qs = qs.filter(warehouse_id=p["warehouse"])
        if p.get("store"):
            qs = qs.filter(warehouse__store_id=p["store"])
        if p.get("search"):
            qs = qs.filter(
                Q(variant__sku__icontains=p["search"])
                | Q(variant__product__name__icontains=p["search"])
            )
        if p.get("low") == "true":
            qs = qs.filter(on_hand__lte=F("reserved") + F("alert_threshold"))
        return qs


class MovementSerializer(serializers.ModelSerializer):
    class Meta:
        model = StockMovement
        fields = "__all__"


class MovementViewSet(SearchMixin, viewsets.ReadOnlyModelViewSet):
    search_fields = ("reference", "kind", "balance__variant__sku")
    serializer_class = MovementSerializer
    queryset = StockMovement.objects.all().order_by("-pk")

    def get_queryset(self):
        ids = store_ids(self.request.user, "manage_stock")
        if not ids:
            raise PermissionDenied()
        qs = self.queryset.filter(balance__warehouse__store_id__in=ids)
        if self.request.query_params.get("balance"):
            qs = qs.filter(balance_id=self.request.query_params["balance"])
        return qs


class ReservationSerializer(serializers.ModelSerializer):
    class Meta:
        model = InventoryReservation
        fields = "__all__"


class ReservationViewSet(MovementViewSet):
    search_fields = ("status", "balance__variant__sku")
    serializer_class = ReservationSerializer
    queryset = InventoryReservation.objects.all().order_by("-pk")


class DocumentSerializer(serializers.ModelSerializer):
    items = ItemInput(many=True)

    class Meta:
        model = StockDocument
        fields = "__all__"
        read_only_fields = ["status", "created_by", "posted_by", "posted_at"]

    def validate(self, data):
        if self.instance and self.instance.status != "DRAFT":
            raise BusinessError("Chứng từ đã ghi sổ/hủy không thể sửa.", "IMMUTABLE_DOCUMENT")
        warehouse = data.get("warehouse", self.instance.warehouse if self.instance else None)
        require(self.context["request"].user, "manage_stock", warehouse.store_id)
        kind = data.get("kind", self.instance.kind if self.instance else None)
        rows = data.get("items", [])
        if "items" in data and (not rows or len({r["variant"].pk for r in rows}) != len(rows)):
            raise serializers.ValidationError({"items": "Cần các dòng hàng không trùng."})
        if any(r["quantity"] == 0 or (kind != "ADJUST" and r["quantity"] < 0) for r in rows):
            raise serializers.ValidationError({"items": "Số lượng không hợp lệ."})
        if "reason" in data and not data["reason"].strip():
            raise serializers.ValidationError({"reason": "Cần lý do."})
        return data

    @transaction.atomic
    def create(self, data):
        rows = data.pop("items")
        doc = StockDocument.objects.create(created_by=self.context["request"].user, **data)
        for row in rows:
            StockDocumentItem.objects.create(document=doc, **row)
        audit(self.context["request"].user, "document.create", doc, doc.warehouse.store)
        return doc

    @transaction.atomic
    def update(self, instance, data):
        # Serialize draft edits against posting; warehouse is immutable once created.
        if "warehouse" in data and data["warehouse"].pk != instance.warehouse_id:
            raise serializers.ValidationError({"warehouse": "Không đổi kho; hãy tạo chứng từ mới."})
        lock_warehouses(instance.warehouse_id)
        instance = StockDocument.objects.select_for_update().get(pk=instance.pk)
        if instance.status != "DRAFT":
            raise BusinessError("Chứng từ không còn ở nháp.", "IMMUTABLE_DOCUMENT")
        rows = data.pop("items", None)
        for k, v in data.items():
            setattr(instance, k, v)
        instance.save()
        if rows is not None:
            instance.items.all().delete()
            for row in rows:
                StockDocumentItem.objects.create(document=instance, **row)
        audit(self.context["request"].user, "document.update", instance, instance.warehouse.store)
        return instance


class DocumentViewSet(viewsets.ModelViewSet):
    serializer_class = DocumentSerializer
    queryset = StockDocument.objects.prefetch_related("items").all().order_by("-pk")
    http_method_names = ["get", "post", "patch", "head", "options"]

    def get_queryset(self):
        ids = store_ids(self.request.user, "manage_stock")
        if not ids:
            raise PermissionDenied()
        qs = self.queryset.filter(warehouse__store_id__in=ids)
        if self.request.query_params.get("search"):
            qs = qs.filter(reason__icontains=self.request.query_params["search"][:200])
        return qs

    @action(detail=True, methods=["post"], url_path="post")
    def post_document(self, request, pk=None):
        return Response(self.get_serializer(post_document(self.get_object().pk, request.user)).data)

    @action(detail=True, methods=["post"])
    def cancel(self, request, pk=None):
        return Response(
            self.get_serializer(post_document(self.get_object().pk, request.user, True)).data
        )


class TransferSerializer(serializers.ModelSerializer):
    items = ItemInput(many=True)

    class Meta:
        model = StockTransfer
        fields = "__all__"
        read_only_fields = ["status", "created_by", "approved_at", "dispatched_at", "received_at"]

    def validate(self, data):
        source = data["source"]
        destination = data["destination"]
        rows = data["items"]
        require(self.context["request"].user, "manage_stock", source.store_id)
        if source == destination:
            raise serializers.ValidationError("Kho nguồn và đích phải khác nhau.")
        if (
            not rows
            or len({r["variant"].pk for r in rows}) != len(rows)
            or any(r["quantity"] <= 0 for r in rows)
        ):
            raise serializers.ValidationError("Cần dòng hàng dương và không trùng.")
        return data

    @transaction.atomic
    def create(self, data):
        rows = data.pop("items")
        t = StockTransfer.objects.create(created_by=self.context["request"].user, **data)
        for row in rows:
            StockTransferItem.objects.create(transfer=t, **row)
        audit(
            self.context["request"].user,
            "transfer.create",
            t,
            t.source.store,
            destination_store=t.destination.store_id,
        )
        return t


class TransferViewSet(viewsets.ModelViewSet):
    serializer_class = TransferSerializer
    queryset = StockTransfer.objects.prefetch_related("items").all().order_by("-pk")
    http_method_names = ["get", "post", "head", "options"]

    def get_queryset(self):
        ids = store_ids(self.request.user, "manage_stock")
        if not ids:
            raise PermissionDenied()
        qs = self.queryset.filter(Q(source__store_id__in=ids) | Q(destination__store_id__in=ids))
        if self.request.query_params.get("search"):
            qs = qs.filter(reason__icontains=self.request.query_params["search"][:200])
        return qs

    def do(self, request, action):
        return Response(
            self.get_serializer(
                transition_transfer(self.get_object().pk, action, request.user)
            ).data
        )

    @action(detail=True, methods=["post"])
    def approve(self, request, pk=None):
        return self.do(request, "approve")

    @action(detail=True, methods=["post"], url_path="dispatch")
    def dispatch_transfer(self, request, pk=None):
        return self.do(request, "dispatch")

    @action(detail=True, methods=["post"])
    def receive(self, request, pk=None):
        obj = self.get_object()
        require(request.user, "manage_stock", obj.destination.store_id)
        if "items" in request.data:
            s = ItemInput(data=request.data["items"], many=True)
            s.is_valid(raise_exception=True)
            actual = sorted((r["variant"].pk, r["quantity"]) for r in s.validated_data)
            expected = sorted(obj.items.values_list("variant_id", "quantity"))
            if actual != expected:
                audit(
                    request.user,
                    "transfer.receipt_mismatch",
                    obj,
                    obj.destination.store,
                    expected=expected,
                    actual=actual,
                )
                raise BusinessError(
                    "Số thực nhận khác chứng từ. Cần người có quyền xử lý ngoại lệ; chưa nhận kho.",
                    "RECEIPT_MISMATCH",
                )
        return self.do(request, "receive")

    @action(detail=True, methods=["post"])
    def cancel(self, request, pk=None):
        return self.do(request, "cancel")
