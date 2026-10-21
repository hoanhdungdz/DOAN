import hashlib
import logging
import time
from datetime import timedelta
from types import SimpleNamespace
from unittest.mock import patch
from urllib.parse import parse_qs, urlsplit

import requests
from django.core.cache import cache
from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from apps.accounts.models import FacebookLoginAttempt, SocialIdentity, User
from apps.customers.models import Customer
from common.logging import RedactOAuthQuery

CALLBACK = "http://localhost:5173/api/v1/auth/facebook/callback/"


@override_settings(
    FACEBOOK_LOGIN_ENABLED=True,
    FACEBOOK_APP_ID="123456",
    FACEBOOK_APP_SECRET="test-only-facebook-secret",
    FACEBOOK_REDIRECT_URI=CALLBACK,
    FACEBOOK_GRAPH_VERSION="v25.0",
)
class FacebookLoginTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.existing = User.objects.create_user("existing@test.invalid", "Test-password-2026!")
        cls.customer = Customer.objects.create(
            user=cls.existing, name="Existing", email=cls.existing.email
        )

    def setUp(self):
        cache.clear()
        self.client = self.browser()

    def browser(self):
        client = APIClient(enforce_csrf_checks=True)
        client.defaults["HTTP_HOST"] = "localhost:5173"
        return client

    def start_response(self, body=None, client=None):
        client = client or self.client
        token = client.get("/api/v1/auth/csrf/").json()["csrfToken"]
        return client.post(
            "/api/v1/auth/facebook/start/", body or {}, format="json", HTTP_X_CSRFTOKEN=token
        )

    def start(self, body=None):
        result = self.start_response(body)
        self.assertEqual(result.status_code, 200, result.content)
        self.assertIn("no-store", result["Cache-Control"])
        url = result.json()["authorization_url"]
        self.assertTrue(url.startswith("https://www.facebook.com/v25.0/dialog/oauth?"))
        self.assertNotIn("test-only-facebook-secret", url)
        return {k: v[0] for k, v in parse_qs(urlsplit(url).query).items()}

    def finish(self, query, debug=None, profile=None, error=None, client=None, token_payload=None):
        debug_data = {
            "is_valid": True,
            "app_id": "123456",
            "user_id": "987654",
            "type": "USER",
            "expires_at": int(time.time()) + 300,
            "data_access_expires_at": int(time.time()) + 3600,
            **(debug or {}),
        }
        profile_data = {
            "id": "987654",
            "email": "new@test.invalid",
            "name": "Facebook customer",
            **(profile or {}),
        }
        values = [
            token_payload if token_payload is not None else {"access_token": "test-user-token"},
            {"data": debug_data},
            profile_data,
        ]
        with patch("apps.accounts.facebook_login.requests.Session") as mock:
            http = mock.return_value.__enter__.return_value
            http.get.side_effect = [
                SimpleNamespace(status_code=200, json=lambda v=v: v) for v in values
            ]
            result = (client or self.client).get(
                "/api/v1/auth/facebook/callback/",
                {
                    "state": query["state"],
                    **({"error": error} if error else {"code": "test-private-code"}),
                },
            )
            return result, http.get.call_args_list

    def test_disabled_provider_and_missing_config(self):
        for config in [{"FACEBOOK_LOGIN_ENABLED": False}, {"FACEBOOK_APP_SECRET": ""}]:
            with self.subTest(config=config), override_settings(**config):
                self.assertFalse(self.client.get("/api/v1/features/").json()["facebook_login"])
                self.assertEqual(self.start_response().status_code, 503)
        self.assertFalse(FacebookLoginAttempt.objects.exists())

    def test_start_is_csrf_protected_post_and_link_requires_login(self):
        self.assertEqual(self.client.get("/api/v1/auth/facebook/start/").status_code, 405)
        self.assertEqual(
            self.client.post("/api/v1/auth/facebook/start/", {}, format="json").json()["code"],
            "CSRF_FAILED",
        )
        self.assertEqual(self.start_response({"link_account": True}).status_code, 403)
        self.assertFalse(FacebookLoginAttempt.objects.exists())

    def test_start_binds_exact_callback_and_rejects_unsafe_destination(self):
        query = self.start({"next": "https://attacker.invalid/"})
        self.assertEqual(query["redirect_uri"], CALLBACK)
        self.assertEqual(query["scope"], "public_profile,email")
        attempt = FacebookLoginAttempt.objects.get(
            pk=hashlib.sha256(query["state"].encode()).hexdigest()
        )
        self.assertEqual(attempt.next_path, "")
        self.assertEqual(
            attempt.session_hash,
            hashlib.sha256(self.client.session.session_key.encode()).hexdigest(),
        )
        with override_settings(FACEBOOK_REDIRECT_URI=CALLBACK.replace("localhost", "127.0.0.1")):
            self.assertEqual(self.start_response().status_code, 503)
        with override_settings(APP_ENV="production"):
            self.assertEqual(self.start_response().status_code, 503)

    def test_success_checks_provider_and_creates_only_customer_permissions(self):
        result, calls = self.finish(self.start({"next": "/orders/12"}))
        self.assertEqual(result["Location"], "/auth/facebook/complete?next=%2Forders%2F12&linked=0")
        self.assertIn("no-store", result["Cache-Control"])
        self.assertEqual(result["Referrer-Policy"], "no-referrer")
        self.assertEqual(len(calls), 3)
        self.assertEqual(calls[0].kwargs["params"]["redirect_uri"], CALLBACK)
        self.assertEqual(calls[1].kwargs["params"]["input_token"], "test-user-token")
        self.assertEqual(calls[2].kwargs["params"]["fields"], "id,name,email")
        self.assertTrue(calls[2].kwargs["params"]["appsecret_proof"])
        for call in calls:
            self.assertFalse(call.kwargs["allow_redirects"])
            self.assertEqual(call.kwargs["timeout"], (3.05, 10))
        user = User.objects.get(email="new@test.invalid")
        self.assertFalse(user.has_usable_password())
        self.assertFalse(user.is_staff or user.is_superuser or user.assignments.exists())
        self.assertEqual(Customer.objects.get(user=user).name, "Facebook customer")
        self.assertTrue(self.client.get("/api/v1/auth/me/").json()["user"]["facebook_linked"])
        self.assertFalse(self.client.get("/api/v1/auth/me/").json()["user"]["google_linked"])
        self.assertIsNotNone(FacebookLoginAttempt.objects.get().used_at)
        self.assertNotIn("test-user-token", result["Location"])

    def test_missing_foreign_expired_and_replayed_state_never_contacts_provider(self):
        query = self.start()
        result, calls = self.finish(query, client=self.browser())
        self.assertIn("facebook_error=invalid_state", result["Location"])
        self.assertEqual(len(calls), 0)
        FacebookLoginAttempt.objects.update(expires_at=timezone.now() - timedelta(seconds=1))
        result, calls = self.finish(query)
        self.assertIn("facebook_error=invalid_state", result["Location"])
        self.assertEqual(len(calls), 0)
        query = self.start()
        self.finish(query)
        result, calls = self.finish(query)
        self.assertIn("facebook_error=invalid_state", result["Location"])
        self.assertEqual(len(calls), 0)
        self.assertEqual(SocialIdentity.objects.count(), 1)

    def test_wrong_app_invalid_type_expiry_and_user_mismatch_rejected(self):
        for changes in [
            {"is_valid": False},
            {"app_id": "foreign-app"},
            {"type": "PAGE"},
            {"expires_at": 0},
            {"expires_at": "bad"},
            {"data_access_expires_at": 1},
            {"user_id": "wrong-subject"},
            {"user_id": "111222"},
        ]:
            with self.subTest(changes=changes):
                cache.clear()
                result, _ = self.finish(self.start(), debug=changes)
                self.assertIn("facebook_error=verification_failed", result["Location"])
                self.assertIsNone(self.client.get("/api/v1/auth/me/").json()["user"])
        self.assertFalse(SocialIdentity.objects.exists())

    def test_existing_email_never_automatically_links(self):
        result, _ = self.finish(
            self.start({"next": "/orders"}), profile={"email": self.existing.email}
        )
        self.assertIn("facebook_error=email_exists", result["Location"])
        self.assertIn("next=%2Forders", result["Location"])
        self.assertFalse(SocialIdentity.objects.exists())
        self.assertEqual(User.objects.count(), 1)

    def test_missing_email_offers_linking_without_creating_fake_email(self):
        result, _ = self.finish(self.start(), profile={"email": None})
        self.assertIn("facebook_error=email_required", result["Location"])
        self.assertEqual(User.objects.count(), 1)
        self.assertFalse(SocialIdentity.objects.exists())

    def test_explicit_link_without_email_keeps_customer_and_google_identity(self):
        SocialIdentity.objects.create(user=self.existing, provider="google", subject="987654")
        self.client.force_login(self.existing)
        result, _ = self.finish(self.start({"link_account": True}), profile={"email": None})
        self.assertEqual(result["Location"], "/auth/facebook/complete?next=%2Fprofile&linked=1")
        self.assertEqual(User.objects.count(), 1)
        self.assertEqual(Customer.objects.get(user=self.existing).pk, self.customer.pk)
        self.assertEqual(SocialIdentity.objects.filter(user=self.existing).count(), 2)

    def test_link_cannot_steal_identity_or_replace_existing_link(self):
        other = User.objects.create_user("other@test.invalid")
        identity = SocialIdentity.objects.create(user=other, provider="facebook", subject="987654")
        self.client.force_login(self.existing)
        result, _ = self.finish(self.start({"link_account": True}))
        self.assertIn("/profile?facebook_error=identity_in_use", result["Location"])
        identity.refresh_from_db()
        self.assertEqual(identity.user_id, other.pk)
        identity.delete()
        SocialIdentity.objects.create(user=self.existing, provider="facebook", subject="123")
        result, _ = self.finish(self.start({"link_account": True}))
        self.assertIn("facebook_error=already_linked", result["Location"])

    def test_known_subject_works_without_email_but_inactive_user_is_blocked(self):
        SocialIdentity.objects.create(user=self.existing, provider="facebook", subject="987654")
        result, _ = self.finish(self.start(), profile={"email": None})
        self.assertTrue(result["Location"].startswith("/auth/facebook/complete?"))
        self.assertEqual(self.client.get("/api/v1/auth/me/").json()["user"]["id"], self.existing.pk)
        self.existing.is_active = False
        self.existing.save()
        self.client = self.browser()
        result, _ = self.finish(self.start())
        self.assertIn("facebook_error=account_unavailable", result["Location"])

    def test_session_account_change_invalidates_link_attempt(self):
        query = self.start()
        self.client.force_login(self.existing)
        result, calls = self.finish(query)
        self.assertIn("facebook_error=invalid_state", result["Location"])
        self.assertEqual(len(calls), 0)

    def test_cancellation_consumes_attempt(self):
        result, calls = self.finish(self.start(), error="access_denied")
        self.assertIn("facebook_error=cancelled", result["Location"])
        self.assertEqual(len(calls), 0)
        self.assertIsNotNone(FacebookLoginAttempt.objects.get().used_at)

    def test_malformed_provider_response_and_network_failure_fail_closed(self):
        result, _ = self.finish(self.start(), token_payload={"access_token": 5})
        self.assertIn("facebook_error=verification_failed", result["Location"])
        result, _ = self.finish(self.start(), profile={"email": "invalid-email"})
        self.assertIn("facebook_error=verification_failed", result["Location"])
        query = self.start()
        with patch("apps.accounts.facebook_login.requests.Session") as mock:
            mock.return_value.__enter__.return_value.get.side_effect = requests.Timeout(
                "private-url"
            )
            result = self.client.get(
                "/api/v1/auth/facebook/callback/", {"state": query["state"], "code": "private"}
            )
        self.assertIn("facebook_error=verification_failed", result["Location"])
        self.assertNotIn("private", result["Location"])

    def test_callback_queries_are_redacted(self):
        record = logging.LogRecord(
            "django.server",
            logging.INFO,
            "",
            1,
            '"GET /api/v1/auth/facebook/callback/?code=private-code&state=private-state HTTP/1.1" 302',
            (),
            None,
        )
        RedactOAuthQuery().filter(record)
        self.assertNotIn("private", record.getMessage())
        self.assertIn("[redacted]", record.getMessage())
