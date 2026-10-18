from django.contrib.auth.models import Group, Permission
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db.models import Q
from rest_framework import serializers, viewsets
from rest_framework.exceptions import PermissionDenied
from common.audit import audit, save_with_audit
from common.models import AuditLog
from apps.accounts.models import User, Employee, RoleAssignment
from apps.accounts.permissions import require, store_ids, is_admin
from apps.customers.models import Customer
from apps.stores.models import Store, Warehouse
from apps.suppliers.models import Supplier
from apps.products.api import CatalogViewSet, catalog_internal
from common.filters import SearchMixin


class StoreSerializer(serializers.ModelSerializer):
    class Meta:
        model = Store
        fields = "__all__"


class WarehouseSerializer(serializers.ModelSerializer):
    store_name = serializers.CharField(source="store.name", read_only=True)

    class Meta:
        model = Warehouse
        fields = "__all__"


class StoreViewSet(CatalogViewSet):
    queryset = Store.objects.all().order_by("pk")
    serializer_class = StoreSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        capability = {
            "sales": "manage_sales",
            "stock": "manage_stock",
            "reports": "view_reports",
        }.get(self.request.query_params.get("scope"))
        return qs.filter(pk__in=store_ids(self.request.user, capability)) if capability else qs


class WarehouseViewSet(CatalogViewSet):
    queryset = Warehouse.objects.select_related("store").all().order_by("pk")
    serializer_class = WarehouseSerializer

    def get_queryset(self):
        # Active warehouse IDs are public fulfillment choices; balances are protected separately.
        qs = super().get_queryset()
        if not catalog_internal(self.request):
            qs = qs.filter(store__is_active=True)
        capability = {"sales": "manage_sales", "stock": "manage_stock"}.get(
            self.request.query_params.get("scope")
        )
        if capability:
            qs = qs.filter(store_id__in=store_ids(self.request.user, capability))
        if self.request.query_params.get("store"):
            qs = qs.filter(store_id=self.request.query_params["store"])
        return qs


class SupplierSerializer(serializers.ModelSerializer):
    class Meta:
        model = Supplier
        fields = "__all__"


class SupplierViewSet(CatalogViewSet):
    queryset = Supplier.objects.all().order_by("pk")
    serializer_class = SupplierSerializer

    def get_queryset(self):
        if not store_ids(self.request.user, "manage_stock"):
            raise PermissionDenied()
        return super().get_queryset()


class AdminViewSet(SearchMixin, viewsets.ModelViewSet):
    http_method_names = ["get", "post", "patch", "head", "options"]

    def initial(self, request, *a, **kw):
        super().initial(request, *a, **kw)
        require(request.user, "manage_accounts")

    def get_queryset(self):
        qs = super().get_queryset()
        search = self.request.query_params.get("search", "")[:200]
        if search:
            names = [f.name for f in qs.model._meta.fields]
            fields = [f for f in ["name", "email", "full_name", "codename"] if f in names]
            if fields:
                q = Q()
                for field in fields:
                    q |= Q(**{field + "__icontains": search})
                qs = qs.filter(q)
        return qs

    def perform_create(self, s):
        save_with_audit(self.request.user, "admin.create", s)

    def perform_update(self, s):
        save_with_audit(self.request.user, "admin.update", s)


class UserSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=False, min_length=8, max_length=128)

    class Meta:
        model = User
        fields = ["id", "email", "full_name", "is_active", "password", "date_joined"]
        read_only_fields = ["date_joined"]

    def validate(self, data):
        if not self.instance and not data.get("password"):
            raise serializers.ValidationError({"password": "Cần mật khẩu cho tài khoản mới."})
        if data.get("password"):
            try:
                validate_password(
                    data["password"], self.instance or User(email=data.get("email", ""))
                )
            except DjangoValidationError as e:
                raise serializers.ValidationError({"password": e.messages})
        if "email" in data:
            data["email"] = data["email"].strip().lower()
        return data

    def create(self, data):
        return User.objects.create_user(**data)

    def update(self, instance, data):
        password = data.pop("password", None)
        for k, v in data.items():
            setattr(instance, k, v)
        if password:
            instance.set_password(password)
        instance.save()
        return instance


class UserViewSet(AdminViewSet):
    queryset = User.objects.all().order_by("pk")
    serializer_class = UserSerializer


class RoleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Group
        fields = ["id", "name", "permissions"]


class RoleViewSet(AdminViewSet):
    queryset = Group.objects.all().order_by("name")
    serializer_class = RoleSerializer


class PermissionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Permission
        fields = ["id", "name", "codename", "content_type"]


class PermissionViewSet(AdminViewSet):
    queryset = Permission.objects.filter(content_type__app_label="accounts").order_by("pk")
    serializer_class = PermissionSerializer
    http_method_names = ["get", "head", "options"]


class AssignmentSerializer(serializers.ModelSerializer):
    group_name = serializers.CharField(source="group.name", read_only=True)
    email = serializers.CharField(source="user.email", read_only=True)

    class Meta:
        model = RoleAssignment
        fields = "__all__"


class AssignmentViewSet(AdminViewSet):
    search_fields = ("user__email", "group__name", "store__name")
    queryset = RoleAssignment.objects.select_related("user", "group").all().order_by("pk")
    serializer_class = AssignmentSerializer
    http_method_names = ["get", "post", "patch", "delete", "head", "options"]

    def perform_destroy(self, instance):
        audit(self.request.user, "assignment.delete", instance, instance.store)
        instance.delete()


class EmployeeSerializer(serializers.ModelSerializer):
    email = serializers.CharField(source="user.email", read_only=True)
    full_name = serializers.CharField(source="user.full_name", read_only=True)

    class Meta:
        model = Employee
        fields = "__all__"


class EmployeeViewSet(SearchMixin, viewsets.ModelViewSet):
    search_fields = ("code", "title", "phone", "user__email", "user__full_name")
    queryset = Employee.objects.select_related("user").all().order_by("pk")
    serializer_class = EmployeeSerializer
    http_method_names = ["get", "post", "patch", "head", "options"]

    def get_queryset(self):
        if is_admin(self.request.user):
            return self.queryset
        ids = store_ids(self.request.user, "manage_people")
        if not ids:
            raise PermissionDenied()
        return self.queryset.filter(user__assignments__store_id__in=ids).distinct()

    def perform_create(self, s):
        require(self.request.user, "manage_accounts")
        s.save()

    def perform_update(self, s):
        if not is_admin(self.request.user) and "user" in s.validated_data:
            raise PermissionDenied("Không được đổi tài khoản của hồ sơ.")
        obj = s.save()
        audit(self.request.user, "employee.update", obj)


class CustomerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Customer
        fields = "__all__"
        read_only_fields = ["user"]


class CustomerViewSet(viewsets.ModelViewSet):
    queryset = Customer.objects.all().order_by("pk")
    serializer_class = CustomerSerializer
    http_method_names = ["get", "patch", "head", "options"]

    def get_queryset(self):
        ids = store_ids(self.request.user, "manage_sales") + store_ids(
            self.request.user, "manage_people"
        )
        if not ids:
            raise PermissionDenied()
        qs = (
            self.queryset
            if is_admin(self.request.user)
            else self.queryset.filter(order__warehouse__store_id__in=ids).distinct()
        )
        if self.request.query_params.get("search"):
            qs = qs.filter(
                Q(name__icontains=self.request.query_params["search"])
                | Q(phone__icontains=self.request.query_params["search"])
            )
        if self.request.query_params.get("store"):
            chosen = int(self.request.query_params["store"])
            if chosen not in ids:
                raise PermissionDenied()
            qs = qs.filter(order__warehouse__store_id=chosen).distinct()
        return qs

    def perform_update(self, s):
        obj = s.save()
        store = (
            obj.order_set.filter(warehouse__store_id__in=store_ids(self.request.user))
            .select_related("warehouse__store")
            .first()
        )
        audit(self.request.user, "customer.update", obj, store.warehouse.store if store else None)


class AuditSerializer(serializers.ModelSerializer):
    class Meta:
        model = AuditLog
        fields = "__all__"


class AuditViewSet(SearchMixin, viewsets.ReadOnlyModelViewSet):
    search_fields = ("action", "object_type", "object_id")
    queryset = AuditLog.objects.all().order_by("-pk")
    serializer_class = AuditSerializer

    def get_queryset(self):
        if is_admin(self.request.user):
            return self.queryset
        ids = store_ids(self.request.user, "view_audit")
        if not ids:
            raise PermissionDenied()
        return self.queryset.filter(Q(store_id__in=ids) | Q(changes__destination_store__in=ids))
