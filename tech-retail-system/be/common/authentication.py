from rest_framework.authentication import SessionAuthentication
from rest_framework.exceptions import PermissionDenied


class CsrfSessionAuthentication(SessionAuthentication):
    def enforce_csrf(self, request):
        try:
            return super().enforce_csrf(request)
        except PermissionDenied as exc:
            # Distinguish a rejection before the view from normal permission
            # failures, so the client can safely refresh and retry once.
            raise PermissionDenied(
                "Phiên bảo mật đã thay đổi. Vui lòng thử lại hoặc tải lại trang.",
                code="CSRF_FAILED",
            ) from exc

    def authenticate(self, request):
        # DRF normally skips CSRF for anonymous requests. Checkout/login need it too.
        if request.method not in ("GET", "HEAD", "OPTIONS", "TRACE"):
            self.enforce_csrf(request)
        return super().authenticate(request)
