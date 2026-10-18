from django.urls import path, include
from rest_framework.routers import DefaultRouter
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView
from apps.accounts.views import CsrfView, AuthView, MeView, ProfileView
from apps.products.api import (
    ProductViewSet,
    VariantViewSet,
    CategoryViewSet,
    BrandViewSet,
    ImageViewSet,
    SpecificationViewSet,
    DefinitionViewSet,
)
from common.resources import (
    StoreViewSet,
    WarehouseViewSet,
    SupplierViewSet,
    UserViewSet,
    RoleViewSet,
    PermissionViewSet,
    AssignmentViewSet,
    EmployeeViewSet,
    CustomerViewSet,
    AuditViewSet,
)
from apps.inventory.api import (
    BalanceViewSet,
    MovementViewSet,
    ReservationViewSet,
    DocumentViewSet,
    TransferViewSet,
)
from apps.orders.api import OrderViewSet, CartView, InvoiceViewSet
from apps.orders.lookup import LookupView
from apps.payments.api import PaymentViewSet
from apps.reports.api import ReportView
from apps.ai_consultation.api import FeatureView, RetrievalView, ChatView

router = DefaultRouter()
for name, view in [
    ("products", ProductViewSet),
    ("variants", VariantViewSet),
    ("categories", CategoryViewSet),
    ("brands", BrandViewSet),
    ("product-images", ImageViewSet),
    ("specifications", SpecificationViewSet),
    ("specification-definitions", DefinitionViewSet),
    ("stores", StoreViewSet),
    ("warehouses", WarehouseViewSet),
    ("suppliers", SupplierViewSet),
    ("users", UserViewSet),
    ("roles", RoleViewSet),
    ("permissions", PermissionViewSet),
    ("assignments", AssignmentViewSet),
    ("employees", EmployeeViewSet),
    ("customers", CustomerViewSet),
    ("audit-logs", AuditViewSet),
    ("inventory", BalanceViewSet),
    ("movements", MovementViewSet),
    ("reservations", ReservationViewSet),
    ("stock-documents", DocumentViewSet),
    ("stock-transfers", TransferViewSet),
    ("orders", OrderViewSet),
    ("payments", PaymentViewSet),
    ("invoices", InvoiceViewSet),
]:
    router.register(name, view, basename=name)
urlpatterns = [
    path("api/v1/", include(router.urls)),
    path("api/v1/auth/csrf/", CsrfView.as_view()),
    path("api/v1/auth/me/", MeView.as_view()),
    path("api/v1/auth/profile/", ProfileView.as_view()),
    path("api/v1/auth/<str:action>/", AuthView.as_view()),
    path("api/v1/carts/", CartView.as_view()),
    path("api/v1/order-lookup/<str:action>/", LookupView.as_view()),
    path("api/v1/reports/<str:kind>/", ReportView.as_view()),
    path("api/v1/features/", FeatureView.as_view()),
    path("api/v1/ai/retrieval/", RetrievalView.as_view()),
    path("api/v1/ai/chat/", ChatView.as_view()),
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/docs/", SpectacularSwaggerView.as_view(url_name="schema")),
]
