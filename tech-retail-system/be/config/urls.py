from django.urls import path, include
from django.views.generic import RedirectView
from rest_framework.routers import DefaultRouter
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView
from apps.accounts.views import CsrfView, AuthView, MeView, ProfileView
from apps.accounts.google_login import GoogleStartView, GoogleCallbackView
from apps.accounts.facebook_login import FacebookStartView, FacebookCallbackView
from apps.products.api import (
    ProductViewSet,
    VariantViewSet,
    CategoryViewSet,
    BrandViewSet,
    ImageViewSet,
    SpecificationViewSet,
    DefinitionViewSet,
)
from apps.products.feedback import (
    ProductFeedbackView,
    FeedbackReplyView,
    FeedbackVoteView,
    FeedbackReportView,
    FeedbackPhotoView,
    FeedbackAdminView,
    FeedbackModerateView,
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
from apps.orders.api import (
    OrderViewSet,
    MyOrderViewSet,
    CartView,
    CartAvailabilityView,
    InvoiceViewSet,
)
from apps.payments.api import PaymentViewSet
from apps.orders.promotion_api import CouponViewSet, PromotionPreviewView
from apps.payments.vnpay_api import (
    VnpayStartView,
    VnpayStatusView,
    VnpayIpnView,
    VnpayReturnView,
    VnpayCheckView,
)
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
    ("coupons", CouponViewSet),
    ("my-orders", MyOrderViewSet),
    ("payments", PaymentViewSet),
    ("invoices", InvoiceViewSet),
]:
    router.register(name, view, basename=name)
urlpatterns = [
    path("", RedirectView.as_view(url="/api/docs/", permanent=False)),
    path("api/v1/", include(router.urls)),
    path("api/v1/products/<slug:slug>/feedback/", ProductFeedbackView.as_view()),
    path("api/v1/feedback/<int:pk>/replies/", FeedbackReplyView.as_view()),
    path("api/v1/feedback/<int:pk>/helpful/", FeedbackVoteView.as_view()),
    path("api/v1/feedback/<int:pk>/report/", FeedbackReportView.as_view()),
    path("api/v1/feedback/photos/<int:pk>/", FeedbackPhotoView.as_view()),
    path("api/v1/feedback-admin/", FeedbackAdminView.as_view()),
    path("api/v1/feedback-admin/<int:pk>/", FeedbackModerateView.as_view()),
    path(
        "api/v1/feedback-admin/replies/<int:pk>/", FeedbackModerateView.as_view(), {"reply": True}
    ),
    path("api/v1/auth/csrf/", CsrfView.as_view()),
    path("api/v1/auth/me/", MeView.as_view()),
    path("api/v1/auth/profile/", ProfileView.as_view()),
    path("api/v1/auth/google/start/", GoogleStartView.as_view()),
    path("api/v1/auth/google/callback/", GoogleCallbackView.as_view()),
    path("api/v1/auth/facebook/start/", FacebookStartView.as_view()),
    path("api/v1/auth/facebook/callback/", FacebookCallbackView.as_view()),
    path("api/v1/auth/<str:action>/", AuthView.as_view()),
    path("api/v1/carts/", CartView.as_view()),
    path("api/v1/carts/availability/", CartAvailabilityView.as_view()),
    path("api/v1/checkout/promotions/", PromotionPreviewView.as_view()),
    path("api/v1/reports/<str:kind>/", ReportView.as_view()),
    path("api/v1/features/", FeatureView.as_view()),
    path("api/v1/my-orders/<int:order_id>/vnpay/", VnpayStartView.as_view()),
    path("api/v1/payments/vnpay/attempts/<str:reference>/", VnpayStatusView.as_view()),
    path("api/v1/payments/vnpay/attempts/<str:reference>/check/", VnpayCheckView.as_view()),
    path("api/v1/payments/vnpay/ipn/", VnpayIpnView.as_view()),
    path("api/v1/payments/vnpay/return/", VnpayReturnView.as_view()),
    path("api/v1/ai/retrieval/", RetrievalView.as_view()),
    path("api/v1/ai/chat/", ChatView.as_view()),
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/docs/", SpectacularSwaggerView.as_view(url_name="schema")),
]
