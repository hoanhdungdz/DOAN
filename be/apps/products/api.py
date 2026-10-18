from decimal import Decimal, InvalidOperation
from django.db.models import Q, F, Exists, OuterRef, Subquery
from rest_framework import serializers, viewsets
from drf_spectacular.utils import extend_schema_field
from common.errors import BusinessError
from common.audit import audit, save_with_audit
from django.db import transaction
from apps.accounts.permissions import require, is_admin
from .models import (
    Category,
    Brand,
    Product,
    ProductVariant,
    ProductImage,
    ProductSpecification,
    SpecificationDefinition,
)
from .quality import contradicts_used_title


def catalog_internal(request):
    return bool(
        request
        and is_admin(request.user)
        and (
            request.query_params.get("internal") == "true"
            or request.method in ("POST", "PATCH", "DELETE")
        )
    )


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = "__all__"


class BrandSerializer(serializers.ModelSerializer):
    class Meta:
        model = Brand
        fields = "__all__"


class ImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductImage
        fields = ["id", "url", "display_order"]


class SpecSerializer(serializers.ModelSerializer):
    name = serializers.CharField(source="definition.name", read_only=True)

    def validate(self, data):
        numeric = data.get("numeric_value", getattr(self.instance, "numeric_value", None))
        unit = data.get("unit", getattr(self.instance, "unit", ""))
        if numeric is not None and not unit.strip():
            raise serializers.ValidationError({"unit": "Giá trị số cần đơn vị rõ ràng."})
        return data

    class Meta:
        model = ProductSpecification
        fields = ["id", "name", "definition", "value", "numeric_value", "unit", "product"]


class VariantSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source="product.name", read_only=True)
    product_slug = serializers.CharField(source="product.slug", read_only=True)
    image = serializers.SerializerMethodField()
    stock = serializers.SerializerMethodField()

    def validate(self, data):
        product = data.get("product", getattr(self.instance, "product", None))
        condition = data.get("condition", getattr(self.instance, "condition", ""))
        if product and contradicts_used_title(product.name, condition):
            raise serializers.ValidationError(
                {"condition": "Tên sản phẩm ghi hàng cũ; không thể gắn tình trạng Mới."}
            )
        return data

    class Meta:
        model = ProductVariant
        fields = [
            "id",
            "product",
            "product_name",
            "product_slug",
            "sku",
            "name",
            "price",
            "condition",
            "warranty_months",
            "attributes",
            "is_active",
            "image",
            "stock",
        ]

    def get_image(self, v) -> str:
        im = next(iter(v.product.images.all()), None)
        return im.url if im else ""

    def validate_attributes(self, value):
        if not isinstance(value, dict):
            raise serializers.ValidationError("Thuộc tính cần là JSON object.")
        return value

    def get_stock(self, v) -> list[dict]:
        request = self.context.get("request")
        store = request.query_params.get("store") if request else None
        balances = v.balances.select_related("warehouse__store").filter(
            warehouse__is_active=True, warehouse__store__is_active=True
        )
        if store:
            balances = balances.filter(warehouse__store_id=store)
        return [
            {
                "warehouse": b.warehouse_id,
                "store": b.warehouse.store_id,
                "store_name": b.warehouse.store.name,
                "available": b.available,
            }
            for b in balances
        ]


class ProductSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source="category.name", read_only=True)
    brand_name = serializers.CharField(source="brand.name", read_only=True)
    variants = serializers.SerializerMethodField()
    images = ImageSerializer(many=True, read_only=True)
    specifications = SpecSerializer(many=True, read_only=True)

    def validate(self, data):
        name = data.get("name", getattr(self.instance, "name", ""))
        if self.instance and any(
            contradicts_used_title(name, variant.condition)
            for variant in self.instance.variants.filter(is_active=True)
        ):
            raise serializers.ValidationError(
                {
                    "name": "Tên ghi hàng cũ nhưng biến thể đang là hàng mới; sửa tình trạng biến thể trước."
                }
            )
        return data

    class Meta:
        model = Product
        exclude = ["source_snapshot"]
        read_only_fields = ["source_namespace", "source_id", "original_slug", "source_url"]

    @extend_schema_field(VariantSerializer(many=True))
    def get_variants(self, product):
        request = self.context.get("request")
        internal = catalog_internal(request)
        variants = [v for v in product.variants.all() if internal or v.is_active]
        return VariantSerializer(variants, many=True, context=self.context).data


class CatalogViewSet(viewsets.ModelViewSet):
    http_method_names = ["get", "post", "patch", "head", "options"]

    def get_queryset(self):
        qs = super().get_queryset()
        internal = catalog_internal(self.request)
        if not internal and hasattr(qs.model, "is_active"):
            qs = qs.filter(is_active=True)
        if not internal and qs.model in (ProductImage, ProductSpecification):
            qs = qs.filter(
                product__is_active=True,
                product__category__is_active=True,
                product__brand__is_active=True,
            )
        search = self.request.query_params.get("search", "")
        if search and qs.model not in (Product, ProductVariant):
            if any(f.name == "name" for f in qs.model._meta.fields):
                qs = qs.filter(name__icontains=search[:200])
        return qs

    def perform_create(self, s):
        require(self.request.user, "manage_accounts")
        extra = {}
        if s.Meta.model is Product:
            import uuid

            extra = {"source_namespace": "manual", "source_id": uuid.uuid4().hex}
        save_with_audit(self.request.user, "catalog.create", s, **extra)

    def perform_update(self, s):
        require(self.request.user, "manage_accounts")
        save_with_audit(self.request.user, "catalog.update", s)

    @transaction.atomic
    def perform_destroy(self, instance):
        require(self.request.user, "manage_accounts")
        audit(self.request.user, "catalog.delete", instance)
        instance.delete()


class CategoryViewSet(CatalogViewSet):
    queryset = Category.objects.all().order_by("name")
    serializer_class = CategorySerializer


class BrandViewSet(CatalogViewSet):
    queryset = Brand.objects.all().order_by("name")
    serializer_class = BrandSerializer


def filter_catalog(qs, params, variant=False, include_inactive=False):
    prefix = "product__" if variant else ""
    search = params.get("search", "").strip()[:200]
    if search:
        qs = qs.filter(
            Q(**{prefix + "name__icontains": search})
            | Q(**{prefix + "brand__name__icontains": search})
            | Q(**{("sku" if variant else "variants__sku") + "__icontains": search})
        )
    for field in ["category", "brand"]:
        if params.get(field):
            qs = qs.filter(**{prefix + field + "_id": params[field]})
    # All variant filters must match the same sellable variant. EXISTS also avoids
    # duplicate products when a product has multiple prices or warehouses.
    eligible = qs if variant else ProductVariant.objects.filter(product_id=OuterRef("pk"))
    if not include_inactive:
        eligible = eligible.filter(is_active=True)
    variant_filters = {}
    for param, lookup in [("price_min", "gte"), ("price_max", "lte")]:
        if params.get(param):
            try:
                value = Decimal(params[param])
            except InvalidOperation:
                raise BusinessError("Giá lọc không hợp lệ.", "INVALID_FILTER", 400)
            if not value.is_finite() or value < 0:
                raise BusinessError("Giá lọc không hợp lệ.", "INVALID_FILTER", 400)
            variant_filters["price__" + lookup] = value
    if params.get("condition"):
        variant_filters["condition"] = params["condition"]
    if params.get("spec"):
        qs = qs.filter(**{prefix + "raw_specs__icontains": params["spec"][:200]})
    if params.get("spec_definition"):
        lookup = {prefix + "specifications__definition_id": params["spec_definition"]}
        if (params.get("spec_min") or params.get("spec_max")) and not params.get("spec_unit"):
            raise BusinessError(
                "Lọc thông số số cần spec_unit để không so sánh khác đơn vị.",
                "SPEC_UNIT_REQUIRED",
                400,
            )
        if params.get("spec_unit"):
            lookup[prefix + "specifications__unit"] = params["spec_unit"][:30]
        if params.get("spec_min"):
            lookup[prefix + "specifications__numeric_value__gte"] = params["spec_min"]
        if params.get("spec_max"):
            lookup[prefix + "specifications__numeric_value__lte"] = params["spec_max"]
        qs = qs.filter(**lookup)
    if params.get("in_stock") == "true":
        variant_filters.update(
            {
                "balances__on_hand__gt": F("balances__reserved"),
                "balances__warehouse__is_active": True,
                "balances__warehouse__store__is_active": True,
            }
        )
        if params.get("store"):
            variant_filters["balances__warehouse__store_id"] = params["store"]
    if variant:
        qs = qs.filter(**variant_filters)
    else:
        eligible = eligible.filter(**variant_filters)
        if not include_inactive or variant_filters:
            qs = qs.filter(Exists(eligible))
        qs = qs.annotate(catalog_price=Subquery(eligible.order_by("price").values("price")[:1]))
    sort = params.get("sort", "name")
    price_field = "price" if variant else "catalog_price"
    ordering = {"name": prefix + "name", "price": price_field, "-price": "-" + price_field}.get(
        sort, prefix + "name"
    )
    return qs.distinct().order_by(ordering, "pk")


class ProductViewSet(CatalogViewSet):
    queryset = (
        Product.objects.select_related("category", "brand")
        .prefetch_related("images", "variants", "specifications__definition")
        .all()
        .order_by("pk")
    )
    serializer_class = ProductSerializer
    lookup_field = "slug"

    def get_queryset(self):
        qs = super().get_queryset()
        if not catalog_internal(self.request):
            qs = qs.filter(category__is_active=True, brand__is_active=True)
        return filter_catalog(
            qs,
            self.request.query_params,
            include_inactive=catalog_internal(self.request),
        )


class VariantViewSet(CatalogViewSet):
    queryset = (
        ProductVariant.objects.select_related("product")
        .prefetch_related("product__images")
        .all()
        .order_by("pk")
    )
    serializer_class = VariantSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        if not catalog_internal(self.request):
            qs = qs.filter(
                product__is_active=True,
                product__category__is_active=True,
                product__brand__is_active=True,
            )
        return filter_catalog(
            qs, self.request.query_params, True, include_inactive=catalog_internal(self.request)
        )


class ImageWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductImage
        fields = "__all__"


class ImageViewSet(CatalogViewSet):
    http_method_names = ["get", "post", "patch", "delete", "head", "options"]
    queryset = ProductImage.objects.all().order_by("id")
    serializer_class = ImageWriteSerializer


class SpecificationViewSet(CatalogViewSet):
    http_method_names = ["get", "post", "patch", "delete", "head", "options"]
    queryset = ProductSpecification.objects.select_related("definition").all().order_by("id")
    serializer_class = SpecSerializer


class DefinitionSerializer(serializers.ModelSerializer):
    class Meta:
        model = SpecificationDefinition
        fields = "__all__"


class DefinitionViewSet(CatalogViewSet):
    queryset = SpecificationDefinition.objects.all().order_by("id")
    serializer_class = DefinitionSerializer
