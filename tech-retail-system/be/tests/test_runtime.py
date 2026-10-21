from django.test import SimpleTestCase
from django.conf import settings
from rest_framework.test import APIClient


class RuntimeEntryPointTests(SimpleTestCase):
    def test_backend_root_opens_api_documentation(self):
        response = self.client.get("/")
        self.assertRedirects(response, "/api/docs/", fetch_redirect_response=False)

    def test_swagger_page_can_render_without_a_database_connection(self):
        response = self.client.get("/api/docs/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'id="swagger-ui"')


class CsrfRecoveryContractTests(SimpleTestCase):
    def test_missing_csrf_is_distinct_from_a_business_permission_denial(self):
        client = APIClient(enforce_csrf_checks=True)
        response = client.post("/api/v1/auth/login/", {}, format="json")
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()["code"], "CSRF_FAILED")

    def test_stale_token_is_blocked_and_refresh_uses_the_current_cookie(self):
        client = APIClient(enforce_csrf_checks=True)
        stale = client.get("/api/v1/auth/csrf/").json()["csrfToken"]
        other_tab = APIClient(enforce_csrf_checks=True)
        other_tab.get("/api/v1/auth/csrf/")
        client.cookies[settings.CSRF_COOKIE_NAME] = other_tab.cookies[
            settings.CSRF_COOKIE_NAME
        ].value
        blocked = client.post("/api/v1/auth/login/", {}, format="json", HTTP_X_CSRFTOKEN=stale)
        self.assertEqual(blocked.status_code, 403)
        self.assertEqual(blocked.json()["code"], "CSRF_FAILED")
        fresh_response = client.get("/api/v1/auth/csrf/")
        self.assertIn("no-store", fresh_response["Cache-Control"])
        accepted = client.post(
            "/api/v1/auth/login/",
            {},
            format="json",
            HTTP_X_CSRFTOKEN=fresh_response.json()["csrfToken"],
        )
        # Reaches input validation, without needing a user/database or bypassing CSRF.
        self.assertEqual(accepted.status_code, 400)
        self.assertEqual(accepted.json()["code"], "VALIDATION_ERROR")
