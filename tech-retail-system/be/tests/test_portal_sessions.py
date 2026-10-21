from django.conf import settings
from django.core.cache import cache
from django.core.exceptions import ImproperlyConfigured
from django.contrib.sessions.models import Session
from django.utils import timezone
from datetime import timedelta
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from .factories import checkout, scenario
from apps.accounts.models import User
from apps.orders.services import create_order


@override_settings(
    ADMIN_FRONTEND_URL="http://localhost:5174",
    CUSTOMER_FRONTEND_URL="http://localhost:5173",
    CSRF_TRUSTED_ORIGINS=["http://localhost:5173", "http://localhost:5174"],
)
class PortalSessionTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.s = scenario()

    def setUp(self):
        cache.clear()
        # One cookie jar for both ports, exactly as a browser on localhost behaves.
        self.browser = APIClient(enforce_csrf_checks=True)

    def call(self, path, host="localhost:5173", method="get", body=None, token=None, origin=None):
        extra = {"HTTP_HOST": host}
        if token:
            extra["HTTP_X_CSRFTOKEN"] = token
        if origin:
            extra["HTTP_ORIGIN"] = origin
        return getattr(self.browser, method)("/api/v1/" + path, body or {}, format="json", **extra)

    def token(self, host="localhost:5173", origin=None):
        response = self.call("auth/csrf/", host, origin=origin)
        self.assertEqual(response.status_code, 200, response.content)
        return response.json()["csrfToken"]

    def login(self, who, host="localhost:5173", origin=None):
        token = self.token(host, origin)
        response = self.call(
            "auth/login/",
            host,
            "post",
            {
                "email": self.s[who].email,
                "password": "Test-password-2026!",
            },
            token,
            origin,
        )
        self.assertEqual(response.status_code, 200, response.content)
        return response

    def who(self, host="localhost:5173", origin=None):
        response = self.call("auth/me/", host, origin=origin)
        self.assertEqual(response.status_code, 200, response.content)
        return response.json()["user"]

    def test_open_store_after_admin_login_preserves_customer_and_does_not_inherit_admin(self):
        self.login("customer")
        customer_session = self.browser.cookies[settings.SESSION_COOKIE_NAME].value
        customer_csrf = self.browser.cookies[settings.CSRF_COOKIE_NAME].value
        self.assertIsNone(self.who("localhost:5174"))
        response = self.login("admin", "localhost:5174")
        self.assertNotIn(settings.SESSION_COOKIE_NAME, response.cookies)
        staff_cookie = response.cookies[settings.SESSION_COOKIE_NAME + "_staff"]
        self.assertTrue(staff_cookie["httponly"])
        self.assertEqual(staff_cookie["samesite"], settings.SESSION_COOKIE_SAMESITE)
        self.assertEqual(self.browser.cookies[settings.SESSION_COOKIE_NAME].value, customer_session)
        self.assertEqual(self.browser.cookies[settings.CSRF_COOKIE_NAME].value, customer_csrf)
        self.assertNotEqual(staff_cookie.value, customer_session)
        # Clicking the link is just a GET to the customer origin; it has no credential hand-off.
        self.assertEqual(self.who()["id"], self.s["customer"].pk)
        self.assertEqual(self.who("localhost:5174")["id"], self.s["admin"].pk)

    def test_admin_only_login_leaves_store_anonymous(self):
        self.login("admin", "localhost:5174")
        self.assertIsNone(self.who())
        self.assertEqual(self.who("localhost:5174")["id"], self.s["admin"].pk)

    def test_logout_and_new_login_only_change_the_selected_portal(self):
        self.login("customer")
        self.login("admin", "localhost:5174")
        response = self.call(
            "auth/logout/", "localhost:5174", "post", token=self.token("localhost:5174")
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.cookies[settings.SESSION_COOKIE_NAME + "_staff"]["max-age"], 0)
        self.assertNotIn(settings.SESSION_COOKIE_NAME, response.cookies)
        self.assertIsNone(self.who("localhost:5174"))
        self.assertEqual(self.who()["id"], self.s["customer"].pk)
        self.login("admin", "localhost:5174")
        self.login("other")
        self.assertEqual(self.who("localhost:5174")["id"], self.s["admin"].pk)
        self.s["admin_two"] = User.objects.create_superuser(
            "second-admin@test.invalid", "Test-password-2026!"
        )
        self.login("admin_two", "localhost:5174")
        self.assertEqual(self.who()["id"], self.s["other"].pk)
        self.assertEqual(
            self.call("auth/logout/", method="post", token=self.token()).status_code, 200
        )
        self.assertIsNone(self.who())
        self.assertEqual(self.who("localhost:5174")["id"], self.s["admin_two"].pk)

    def test_customer_csrf_token_cannot_be_used_on_staff_port_and_reverse(self):
        self.login("customer")
        self.login("admin", "localhost:5174")
        customer_token, staff_token = self.token(), self.token("localhost:5174")
        for host, token in (("localhost:5174", customer_token), ("localhost:5173", staff_token)):
            response = self.call("auth/logout/", host, "post", token=token)
            self.assertEqual(response.status_code, 403)
            self.assertEqual(response.json()["code"], "CSRF_FAILED")
        self.assertEqual(self.who()["id"], self.s["customer"].pk)
        self.assertEqual(self.who("localhost:5174")["id"], self.s["admin"].pk)

    def test_direct_api_uses_origin_and_customer_cannot_borrow_staff_session_over_cors(self):
        self.login("customer")
        self.login("admin", "localhost:8000", "http://localhost:5174")
        self.assertEqual(
            self.who("localhost:8000", "http://localhost:5174")["id"], self.s["admin"].pk
        )
        self.assertEqual(
            self.who("localhost:8000", "http://localhost:5173")["id"], self.s["customer"].pk
        )
        forbidden = self.call("auth/me/", "localhost:5174", origin="http://localhost:5173")
        self.assertEqual(forbidden.status_code, 403)
        self.assertEqual(forbidden.json()["code"], "PORTAL_ORIGIN_MISMATCH")

    def test_loopback_alias_uses_staff_cookies_and_security_attributes_are_preserved(self):
        with override_settings(SESSION_COOKIE_SECURE=True, CSRF_COOKIE_SECURE=True):
            response = self.login("admin", "127.0.0.1:5174")
            for name in (settings.SESSION_COOKIE_NAME, settings.CSRF_COOKIE_NAME):
                self.assertNotIn(name, response.cookies)
                cookie = response.cookies[name + "_staff"]
                self.assertTrue(cookie["secure"])
                self.assertEqual(cookie["path"], "/")
            self.assertIn("Cookie", response["Vary"])
            self.assertIn("Origin", response["Vary"])
            self.assertEqual(self.who("127.0.0.1:5174")["id"], self.s["admin"].pk)

    def test_owner_permissions_do_not_expand_when_staff_cookie_is_present(self):
        order = create_order(checkout(self.s), self.s["customer"], "portal", "one")
        self.login("customer")
        self.login("admin", "localhost:5174")
        self.assertEqual(self.call(f"my-orders/{order.pk}/").status_code, 200)
        self.assertEqual(self.call(f"my-orders/{order.pk}/", "localhost:5174").status_code, 404)

    def test_staff_cookie_alone_does_not_grant_store_access_to_admin_api(self):
        self.login("admin", "localhost:5174")
        self.assertEqual(self.call("users/").status_code, 403)
        self.login("customer")
        self.assertEqual(self.call("users/").status_code, 403)
        self.assertEqual(self.call("users/", "localhost:5174").status_code, 200)

    def test_expiration_of_either_session_does_not_expire_the_other(self):
        for host, cookie in (
            ("localhost:5174", settings.SESSION_COOKIE_NAME + "_staff"),
            ("localhost:5173", settings.SESSION_COOKIE_NAME),
        ):
            cache.clear()
            self.login("customer")
            self.login("admin", "localhost:5174")
            key = self.browser.cookies[cookie].value
            Session.objects.filter(session_key=key).update(
                expire_date=timezone.now() - timedelta(seconds=1)
            )
            self.assertIsNone(self.who(host))
            other_host = "localhost:5173" if host.endswith("5174") else "localhost:5174"
            other_user = self.s["customer"] if host.endswith("5174") else self.s["admin"]
            self.assertEqual(self.who(other_host)["id"], other_user.pk)

    @override_settings(SESSION_COOKIE_NAME="audit_session", CSRF_COOKIE_NAME="audit_csrf")
    def test_staff_cookie_names_derive_from_configured_names(self):
        self.login("customer")
        self.login("admin", "localhost:5174")
        self.assertTrue(
            {"audit_session", "audit_csrf", "audit_session_staff", "audit_csrf_staff"}.issubset(
                self.browser.cookies.keys()
            )
        )
        self.assertNotIn("sessionid_staff", self.browser.cookies)
        self.assertEqual(self.who()["id"], self.s["customer"].pk)
        self.assertEqual(self.who("localhost:5174")["id"], self.s["admin"].pk)

    @override_settings(
        ADMIN_FRONTEND_URL="https://staff.test.invalid:443",
        ALLOWED_HOSTS=["staff.test.invalid", "localhost", "testserver"],
    )
    def test_default_https_port_is_equivalent_in_host_and_origin(self):
        response = self.call(
            "auth/csrf/", "staff.test.invalid", origin="https://staff.test.invalid"
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn(settings.CSRF_COOKIE_NAME + "_staff", response.cookies)
        self.assertNotIn(settings.CSRF_COOKIE_NAME, response.cookies)
        direct = self.call("auth/csrf/", "testserver", origin="https://staff.test.invalid")
        self.assertIn(settings.CSRF_COOKIE_NAME + "_staff", direct.cookies)

    @override_settings(CUSTOMER_FRONTEND_URL="http://localhost:6173")
    def test_store_link_configuration_comes_from_backend(self):
        response = self.call("features/")
        self.assertEqual(response.json().get("customer_frontend_url"), "http://localhost:6173")

    @override_settings(ADMIN_FRONTEND_URL="http://localhost:5173")
    def test_ambiguous_portal_configuration_is_rejected(self):
        from common.portal_sessions import PortalCookieMiddleware

        with self.assertRaises(ImproperlyConfigured):
            PortalCookieMiddleware(lambda request: None)
        with override_settings(
            ADMIN_FRONTEND_URL="https://localhost:443", CUSTOMER_FRONTEND_URL="http://localhost"
        ):
            with self.assertRaises(ImproperlyConfigured):
                PortalCookieMiddleware(lambda request: None)
