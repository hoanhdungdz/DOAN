import hashlib
import json
import logging
import time
from datetime import timedelta
from types import SimpleNamespace
from unittest.mock import patch
from urllib.parse import parse_qs, urlsplit

import requests
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from django.core.cache import cache
from django.test import TestCase, override_settings
from django.utils import timezone
from google.auth import crypt, jwt
from rest_framework.test import APIClient

from apps.accounts.models import GoogleLoginAttempt, SocialIdentity, User
from apps.customers.models import Customer
from common.logging import RedactOAuthQuery

CALLBACK = "http://testserver/api/v1/auth/google/callback/"


@override_settings(
    GOOGLE_LOGIN_ENABLED=True,
    GOOGLE_CLIENT_ID="test-client.apps.googleusercontent.com",
    GOOGLE_CLIENT_SECRET="test-only-secret",
    GOOGLE_REDIRECT_URIS=[
        CALLBACK,
        "http://127.0.0.1:5173/api/v1/auth/google/callback/",
        "http://localhost:5173/api/v1/auth/google/callback/",
    ],
)
class GoogleLoginTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        private = key.private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.PKCS8,
            serialization.NoEncryption(),
        )
        cls.signer = crypt.RSASigner.from_string(private, key_id="test-key")
        cls.public = (
            key.public_key()
            .public_bytes(
                serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo
            )
            .decode()
        )
        cls.existing = User.objects.create_user("existing@test.invalid", "Test-password-2026!")
        cls.customer = Customer.objects.create(
            user=cls.existing, name="Existing customer", email=cls.existing.email
        )

    def setUp(self):
        cache.clear()
        self.client = APIClient(enforce_csrf_checks=True)

    def start(self, client=None, body=None, **headers):
        client = client or self.client
        token = client.get("/api/v1/auth/csrf/", **headers).json()["csrfToken"]
        response = client.post(
            "/api/v1/auth/google/start/",
            body or {},
            format="json",
            HTTP_X_CSRFTOKEN=token,
            **headers,
        )
        self.assertEqual(response.status_code, 200, response.content)
        self.assertIn("no-store", response["Cache-Control"])
        self.assertNotIn("test-only-secret", response.content.decode())
        return {
            key: values[0]
            for key, values in parse_qs(
                urlsplit(response.json()["authorization_url"]).query
            ).items()
        }

    def token(self, query, **overrides):
        now = int(time.time())
        claims = {
            "iss": "https://accounts.google.com",
            "aud": "test-client.apps.googleusercontent.com",
            "sub": "google-test-subject",
            "email": "new@test.invalid",
            "email_verified": True,
            "name": "Google customer",
            "nonce": query["nonce"],
            "iat": now,
            "exp": now + 300,
            **overrides,
        }
        return jwt.encode(self.signer, claims).decode()

    def finish(self, query, token=None, error=None, client=None):
        token = token or self.token(query)
        response = SimpleNamespace(status_code=200, json=lambda: {"id_token": token})
        certs = SimpleNamespace(status=200, data=json.dumps({"test-key": self.public}).encode())
        with (
            patch("apps.accounts.google_login.requests.Session") as http,
            patch("apps.accounts.google_login.GoogleRequest") as transport,
        ):
            http.return_value.__enter__.return_value.post.return_value = response
            transport.return_value.return_value = certs
            result = (client or self.client).get(
                "/api/v1/auth/google/callback/",
                {"state": query["state"], **({"error": error} if error else {"code": "test-code"})},
            )
            return result, http.return_value.__enter__.return_value.post.call_count

    def test_disabled_provider_has_no_button_flag_or_start(self):
        with override_settings(GOOGLE_LOGIN_ENABLED=False):
            self.assertFalse(self.client.get("/api/v1/features/").json()["google_login"])
            token = self.client.get("/api/v1/auth/csrf/").json()["csrfToken"]
            response = self.client.post(
                "/api/v1/auth/google/start/", {}, format="json", HTTP_X_CSRFTOKEN=token
            )
            self.assertEqual(response.status_code, 503)
            self.assertFalse(GoogleLoginAttempt.objects.exists())

    def test_start_requires_post_and_csrf(self):
        self.assertEqual(self.client.get("/api/v1/auth/google/start/").status_code, 405)
        self.assertEqual(
            self.client.post("/api/v1/auth/google/start/", {}, format="json").json()["code"],
            "CSRF_FAILED",
        )
        self.assertFalse(GoogleLoginAttempt.objects.exists())

    def test_start_uses_pkce_nonce_and_the_same_frontend_host(self):
        import base64

        for host in ("localhost:5173", "127.0.0.1:5173"):
            query = self.start(HTTP_HOST=host)
            self.assertEqual(
                query["redirect_uri"], "http://" + host + "/api/v1/auth/google/callback/"
            )
            self.assertEqual(query["scope"], "openid email profile")
            self.assertEqual(query["code_challenge_method"], "S256")
            attempt = GoogleLoginAttempt.objects.get(
                pk=hashlib.sha256(query["state"].encode()).hexdigest()
            )
            expected = (
                base64.urlsafe_b64encode(hashlib.sha256(attempt.code_verifier.encode()).digest())
                .rstrip(b"=")
                .decode()
            )
            self.assertEqual(query["code_challenge"], expected)
            self.assertEqual(attempt.nonce, query["nonce"])

    def test_success_verifies_signed_token_creates_customer_and_session(self):
        query = self.start(body={"next": "/orders/12"})
        result, calls = self.finish(query)
        self.assertEqual(calls, 1)
        self.assertEqual(result.status_code, 302)
        self.assertEqual(result["Location"], "/auth/google/complete?next=%2Forders%2F12&linked=0")
        self.assertIn("no-store", result["Cache-Control"])
        self.assertEqual(result["Referrer-Policy"], "no-referrer")
        user = User.objects.get(email="new@test.invalid")
        self.assertFalse(user.has_usable_password())
        self.assertFalse(user.is_staff or user.is_superuser or user.assignments.exists())
        self.assertEqual(Customer.objects.get(user=user).name, "Google customer")
        self.assertEqual(self.client.get("/api/v1/auth/me/").json()["user"]["id"], user.pk)
        self.assertTrue(SocialIdentity.objects.filter(user=user, provider="google").exists())
        attempt = GoogleLoginAttempt.objects.get()
        self.assertTrue(attempt.used_at)
        self.assertEqual(attempt.code_verifier, "")

    def test_callback_cannot_be_replayed(self):
        query = self.start()
        self.finish(query)
        replay, calls = self.finish(query)
        self.assertIn("google_error=invalid_state", replay["Location"])
        self.assertEqual(calls, 0)
        self.assertEqual(SocialIdentity.objects.count(), 1)

    def test_missing_wrong_expired_or_foreign_state_never_contacts_google(self):
        query = self.start()
        result, calls = self.finish(query, client=APIClient())
        self.assertIn("google_error=invalid_state", result["Location"])
        self.assertEqual(calls, 0)
        GoogleLoginAttempt.objects.update(expires_at=timezone.now() - timedelta(seconds=1))
        result, calls = self.finish(query)
        self.assertIn("google_error=invalid_state", result["Location"])
        self.assertEqual(calls, 0)
        self.assertIn(
            "google_error=invalid_state",
            self.client.get("/api/v1/auth/google/callback/", {"code": "test"})["Location"],
        )
        self.assertFalse(SocialIdentity.objects.exists())

    def test_real_verifier_rejects_invalid_audience_issuer_expiry_nonce_and_email(self):
        for bad in [
            {"aud": "another-client"},
            {"iss": "https://attacker.invalid"},
            {"exp": int(time.time()) - 100},
            {"nonce": "wrong-nonce"},
            {"email_verified": False},
            {"email": "not-an-email"},
            {"azp": "another-client"},
        ]:
            with self.subTest(bad=bad):
                cache.clear()
                query = self.start()
                result, _ = self.finish(query, token=self.token(query, **bad))
                self.assertIn("google_error=verification_failed", result["Location"])
                self.assertIsNone(self.client.get("/api/v1/auth/me/").json()["user"])
        self.assertFalse(SocialIdentity.objects.exists())

    def test_invalid_signature_is_rejected(self):
        query = self.start()
        signed = self.token(query)
        head, payload, sig = signed.split(".")
        forged = ".".join([head, payload, ("A" if sig[0] != "A" else "B") + sig[1:]])
        result, _ = self.finish(query, token=forged)
        self.assertIn("google_error=verification_failed", result["Location"])
        self.assertFalse(SocialIdentity.objects.exists())

    def test_cancellation_consumes_state_without_exchanging_a_code(self):
        result, calls = self.finish(self.start(), error="access_denied")
        self.assertIn("google_error=cancelled", result["Location"])
        self.assertEqual(calls, 0)
        self.assertIsNotNone(GoogleLoginAttempt.objects.get().used_at)

    def test_existing_email_never_auto_links_or_creates_another_account(self):
        query = self.start(body={"next": "/orders"})
        result, _ = self.finish(query, token=self.token(query, email=self.existing.email))
        self.assertIn("google_error=email_exists", result["Location"])
        self.assertIn("next=%2Forders", result["Location"])
        self.assertEqual(User.objects.count(), 1)
        self.assertFalse(SocialIdentity.objects.exists())
        self.assertIsNone(self.client.get("/api/v1/auth/me/").json()["user"])

    def test_explicit_link_preserves_existing_customer_and_account(self):
        self.client.force_login(self.existing)
        query = self.start(body={"link_account": True})
        result, _ = self.finish(query, token=self.token(query, email=self.existing.email))
        self.assertEqual(result["Location"], "/auth/google/complete?next=%2Fprofile&linked=1")
        self.assertEqual(User.objects.count(), 1)
        self.assertEqual(Customer.objects.get(user=self.existing).pk, self.customer.pk)
        self.assertEqual(SocialIdentity.objects.get().user_id, self.existing.pk)
        self.assertTrue(self.client.get("/api/v1/auth/me/").json()["user"]["google_linked"])

    def test_link_requires_login_and_cannot_steal_an_existing_identity(self):
        token = self.client.get("/api/v1/auth/csrf/").json()["csrfToken"]
        response = self.client.post(
            "/api/v1/auth/google/start/",
            {"link_account": True},
            format="json",
            HTTP_X_CSRFTOKEN=token,
        )
        self.assertEqual(response.status_code, 403)
        other = User.objects.create_user("other@test.invalid")
        identity = SocialIdentity.objects.create(
            user=other, provider="google", subject="google-test-subject"
        )
        self.client.force_login(self.existing)
        query = self.start(body={"link_account": True})
        result, _ = self.finish(query)
        self.assertIn("/profile?google_error=identity_in_use", result["Location"])
        identity.refresh_from_db()
        self.assertEqual(identity.user_id, other.pk)

    def test_known_google_subject_logs_in_to_the_same_account_even_if_email_changes(self):
        SocialIdentity.objects.create(
            user=self.existing, provider="google", subject="google-test-subject"
        )
        result, _ = self.finish(self.start())
        self.assertTrue(result["Location"].startswith("/auth/google/complete?"))
        self.assertEqual(self.client.get("/api/v1/auth/me/").json()["user"]["id"], self.existing.pk)
        self.assertEqual(User.objects.count(), 1)

    def test_disabled_linked_account_cannot_login(self):
        SocialIdentity.objects.create(
            user=self.existing, provider="google", subject="google-test-subject"
        )
        User.objects.filter(pk=self.existing.pk).update(is_active=False)
        result, _ = self.finish(self.start())
        self.assertIn("google_error=account_unavailable", result["Location"])
        self.assertIsNone(self.client.get("/api/v1/auth/me/").json()["user"])

    def test_changed_session_cannot_complete_an_earlier_attempt(self):
        query = self.start()
        self.client.force_login(self.existing)
        result, calls = self.finish(query)
        self.assertIn("google_error=invalid_state", result["Location"])
        self.assertEqual(calls, 0)

    def test_external_return_url_is_discarded_and_unregistered_origin_is_blocked(self):
        result, _ = self.finish(self.start(body={"next": "//attacker.invalid"}))
        self.assertEqual(result["Location"], "/auth/google/complete?next=&linked=0")
        token = self.client.get("/api/v1/auth/csrf/", HTTP_HOST="testserver:9999").json()[
            "csrfToken"
        ]
        response = self.client.post(
            "/api/v1/auth/google/start/",
            {},
            format="json",
            HTTP_HOST="testserver:9999",
            HTTP_X_CSRFTOKEN=token,
        )
        self.assertEqual(response.status_code, 503)

    def test_provider_network_failure_is_safe_and_does_not_create_an_identity(self):
        query = self.start()
        with patch("apps.accounts.google_login.requests.Session") as http:
            http.return_value.__enter__.return_value.post.side_effect = requests.Timeout(
                "sensitive-provider-response"
            )
            result = self.client.get(
                "/api/v1/auth/google/callback/", {"state": query["state"], "code": "private-code"}
            )
        self.assertIn("google_error=verification_failed", result["Location"])
        self.assertNotIn("private-code", result["Location"])
        self.assertNotIn("sensitive-provider-response", result.content.decode())
        self.assertFalse(SocialIdentity.objects.exists())

    def test_development_access_log_redacts_callback_query(self):
        record = logging.LogRecord(
            "django.server",
            logging.INFO,
            "",
            0,
            '"GET %s HTTP/1.1" 302',
            ("/api/v1/auth/google/callback/?code=private-code&state=private-state",),
            None,
        )
        RedactOAuthQuery().filter(record)
        self.assertNotIn("private-code", record.getMessage())
        self.assertNotIn("private-state", record.getMessage())
        self.assertIn("[redacted]", record.getMessage())
