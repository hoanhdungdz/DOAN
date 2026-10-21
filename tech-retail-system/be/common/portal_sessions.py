"""Isolate the staff and customer cookies without changing Django's global settings.

Browsers share cookies across localhost ports. The frontend Host (preserved by
the Vite proxies), or the Origin of a direct API request, selects a cookie jar.
This is session routing, not an authorization grant; all role/owner checks remain.
"""

from urllib.parse import urlsplit

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.http import JsonResponse
from django.utils.cache import patch_vary_headers
from django.utils.deprecation import MiddlewareMixin

LOOPBACK = {"localhost", "127.0.0.1", "::1"}
DEFAULT_PORTS = {"http": 80, "https": 443}


def same_hostname(left, right):
    return left.hostname == right.hostname or (
        left.hostname in LOOPBACK and right.hostname in LOOPBACK
    )


def same_host(left, right):
    # Host headers have no scheme; infer the omitted default port from the
    # configured frontend. Origin headers include their own scheme.
    left_port = left.port or DEFAULT_PORTS.get(left.scheme or right.scheme)
    right_port = right.port or DEFAULT_PORTS.get(right.scheme or left.scheme)
    return same_hostname(left, right) and left_port == right_port


def staff_origin(value):
    try:
        origin = urlsplit(value)
        staff = urlsplit(settings.ADMIN_FRONTEND_URL)
        return (
            origin.scheme == staff.scheme
            and same_host(origin, staff)
            and origin.path in ("", "/")
            and not origin.query
            and not origin.fragment
            and not origin.username
            and not origin.password
        )
    except ValueError:
        return False


class PortalCookieMiddleware(MiddlewareMixin):
    def __init__(self, get_response):
        super().__init__(get_response)
        staff, customer = (
            urlsplit(settings.ADMIN_FRONTEND_URL),
            urlsplit(settings.CUSTOMER_FRONTEND_URL),
        )
        # Browsers omit default ports from Host. Two portals on the same
        # hostname distinguished only by http/https would be ambiguous here.
        ambiguous_default_ports = same_hostname(staff, customer) and all(
            url.port in (None, DEFAULT_PORTS.get(url.scheme)) for url in (staff, customer)
        )
        if same_host(staff, customer) or ambiguous_default_ports:
            raise ImproperlyConfigured(
                "ADMIN_FRONTEND_URL and CUSTOMER_FRONTEND_URL must use distinct frontend hosts/ports."
            )

    def process_request(self, request):
        host = urlsplit("//" + request.get_host())
        staff = urlsplit(settings.ADMIN_FRONTEND_URL)
        customer = urlsplit(settings.CUSTOMER_FRONTEND_URL)
        origin = request.headers.get("Origin", "")
        if same_host(host, staff):
            # A customer-origin fetch to the staff port must not borrow staff
            # credentials just because both origins are in the CORS allow-list.
            if origin and not staff_origin(origin):
                return JsonResponse(
                    {
                        "code": "PORTAL_ORIGIN_MISMATCH",
                        "message": "Vui lòng mở chức năng này từ giao diện quản trị.",
                        "fields": {},
                    },
                    status=403,
                )
            is_staff = True
        elif same_host(host, customer):
            is_staff = False
        else:
            # Supports a separately hosted API with credentialed CORS requests.
            is_staff = staff_origin(origin)
        request.staff_cookie_portal = is_staff
        if is_staff:
            cookies = request.COOKIES.copy()
            for name in (settings.SESSION_COOKIE_NAME, settings.CSRF_COOKIE_NAME):
                # Never fall back to a customer session when staff has not logged in.
                value = cookies.pop(name + "_staff", None)
                cookies.pop(name, None)
                if value is not None:
                    cookies[name] = value
            request.COOKIES = cookies

    def process_response(self, request, response):
        if getattr(request, "staff_cookie_portal", False):
            # Session/CSRF middleware run inside this adapter, preserving their
            # rotation, expiry, HttpOnly/Secure/SameSite and logout behavior.
            for name in (settings.SESSION_COOKIE_NAME, settings.CSRF_COOKIE_NAME):
                if name in response.cookies:
                    original = response.cookies.pop(name)
                    response.cookies[name + "_staff"] = original.value
                    response.cookies[name + "_staff"].update(original)
        patch_vary_headers(response, ("Cookie", "Origin"))
        return response
