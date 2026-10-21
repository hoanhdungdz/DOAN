"""Google OpenID Connect: code + PKCE, verified ID token, session-bound single-use state."""

import base64
import hashlib
import re
import secrets
from datetime import timedelta
from urllib.parse import urlencode, urlsplit

import requests
from django.conf import settings
from django.contrib.auth import login
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.db import IntegrityError, transaction
from django.http import HttpResponseRedirect
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views.decorators.cache import never_cache
from django.views.decorators.debug import sensitive_variables
from drf_spectacular.utils import extend_schema
from google.auth.exceptions import GoogleAuthError
from google.auth.transport.requests import Request as GoogleRequest
from google.oauth2.id_token import verify_oauth2_token
from rest_framework import serializers
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from apps.customers.models import Customer
from common.audit import audit
from common.errors import BusinessError
from .models import GoogleLoginAttempt, SocialIdentity, User

CALLBACK_PATH = "/api/v1/auth/google/callback/"


def google_ready():
    return bool(
        settings.GOOGLE_LOGIN_ENABLED
        and settings.GOOGLE_CLIENT_ID
        and settings.GOOGLE_CLIENT_SECRET
        and settings.GOOGLE_REDIRECT_URIS
    )


def safe_next(value):
    if (
        not isinstance(value, str)
        or len(value) > 500
        or re.search(r"[\\\x00-\x20]", value)
        or not re.fullmatch(r"/(?:orders(?:/[1-9]\d*)?|cart|checkout|profile)(?:\?[^#]*)?", value)
    ):
        return ""
    return value


def digest(value):
    return hashlib.sha256(value.encode()).hexdigest()


def callback_for(request):
    # Stay on the originating frontend hostname so OAuth state and cart cookies survive.
    origin = urlsplit(request.build_absolute_uri("/"))
    for uri in settings.GOOGLE_REDIRECT_URIS:
        parsed = urlsplit(uri)
        if (
            parsed.scheme in ("http", "https")
            and (settings.APP_ENV != "production" or parsed.scheme == "https")
            and not parsed.username
            and not parsed.password
            and not parsed.query
            and not parsed.fragment
            and parsed.path == CALLBACK_PATH
            and (parsed.scheme, parsed.netloc) == (origin.scheme, origin.netloc)
        ):
            return uri
    raise BusinessError(
        "Địa chỉ web này chưa được cấu hình callback Google. Vui lòng mở đúng địa chỉ đăng nhập.",
        "GOOGLE_CALLBACK_NOT_CONFIGURED",
        503,
    )


class StartInput(serializers.Serializer):
    next = serializers.CharField(max_length=500, required=False, allow_blank=True)
    link_account = serializers.BooleanField(default=False)


class StartResponse(serializers.Serializer):
    authorization_url = serializers.URLField()


@method_decorator(never_cache, name="dispatch")
class GoogleStartView(APIView):
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "auth"

    @extend_schema(request=StartInput, responses=StartResponse)
    def post(self, request):
        if not google_ready():
            raise BusinessError(
                "Đăng nhập Google chưa được cấu hình.", "GOOGLE_NOT_CONFIGURED", 503
            )
        data = StartInput(data=request.data)
        data.is_valid(raise_exception=True)
        link_account = data.validated_data["link_account"]
        if link_account and not request.user.is_authenticated:
            raise BusinessError("Đăng nhập trước khi liên kết Google.", "AUTH_REQUIRED", 403)
        redirect_uri = callback_for(request)
        if not request.session.session_key:
            request.session.create()
        state, nonce, verifier = (secrets.token_urlsafe(48) for _ in range(3))
        GoogleLoginAttempt.objects.create(
            state_hash=digest(state),
            session_hash=digest(request.session.session_key),
            nonce=nonce,
            code_verifier=verifier,
            redirect_uri=redirect_uri,
            next_path="/profile"
            if link_account
            else safe_next(data.validated_data.get("next", "")),
            link_account=link_account,
            user=request.user if request.user.is_authenticated else None,
            expires_at=timezone.now() + timedelta(minutes=5),
        )
        challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(
            b"="
        )
        query = urlencode(
            {
                "client_id": settings.GOOGLE_CLIENT_ID,
                "redirect_uri": redirect_uri,
                "response_type": "code",
                "scope": "openid email profile",
                "state": state,
                "nonce": nonce,
                "code_challenge": challenge.decode(),
                "code_challenge_method": "S256",
                "prompt": "select_account",
            }
        )
        return Response(
            {"authorization_url": "https://accounts.google.com/o/oauth2/v2/auth?" + query}
        )


class LoginFailure(Exception):
    pass


def claim_attempt(request):
    state = request.GET.get("state", "")
    if not state or len(state) > 256 or not request.session.session_key:
        raise LoginFailure("invalid_state")
    with transaction.atomic():
        attempt = (
            GoogleLoginAttempt.objects.select_for_update().filter(state_hash=digest(state)).first()
        )
        if (
            not attempt
            or attempt.used_at
            or attempt.expires_at <= timezone.now()
            or not secrets.compare_digest(attempt.session_hash, digest(request.session.session_key))
            or attempt.user_id != (request.user.pk if request.user.is_authenticated else None)
            or request.build_absolute_uri(CALLBACK_PATH) != attempt.redirect_uri
        ):
            raise LoginFailure("invalid_state")
        # Consume in MySQL before contacting Google; concurrent/replayed callbacks cannot log in twice.
        GoogleLoginAttempt.objects.filter(pk=attempt.pk).update(
            used_at=timezone.now(), nonce="", code_verifier=""
        )
    return attempt


@sensitive_variables()
def exchange_and_verify(code, attempt):
    with requests.Session() as http:
        response = http.post(
            "https://oauth2.googleapis.com/token",
            data={
                "client_id": settings.GOOGLE_CLIENT_ID,
                "client_secret": settings.GOOGLE_CLIENT_SECRET,
                "code": code,
                "code_verifier": attempt.code_verifier,
                "grant_type": "authorization_code",
                "redirect_uri": attempt.redirect_uri,
            },
            timeout=(3.05, 10),
            allow_redirects=False,
        )
        if response.status_code != 200:
            raise LoginFailure("verification_failed")
        payload = response.json()
        if not isinstance(payload, dict):
            raise LoginFailure("verification_failed")
        token = payload.get("id_token")
        if not isinstance(token, str) or not token or len(token) > 20000:
            raise LoginFailure("verification_failed")
        transport = GoogleRequest(session=http)

        def fetch_keys(*args, **kwargs):
            kwargs["timeout"] = (3.05, 10)
            return transport(*args, **kwargs)

        claims = verify_oauth2_token(token, fetch_keys, audience=settings.GOOGLE_CLIENT_ID)
    if (
        not isinstance(claims.get("nonce"), str)
        or not secrets.compare_digest(claims["nonce"].encode(), attempt.nonce.encode())
        or not isinstance(claims.get("sub"), str)
        or not 0 < len(claims["sub"]) <= 255
        or claims.get("email_verified") is not True
        or (claims.get("azp") and claims["azp"] != settings.GOOGLE_CLIENT_ID)
    ):
        raise LoginFailure("verification_failed")
    email = claims.get("email")
    if not isinstance(email, str) or len(email) > 254:
        raise LoginFailure("verification_failed")
    validate_email(email)
    return claims


@transaction.atomic
def account_for(claims, attempt, provider="google"):
    identity = (
        SocialIdentity.objects.select_for_update()
        .select_related("user")
        .filter(provider=provider, subject=claims["sub"])
        .first()
    )
    if attempt.link_account:
        user = User.objects.select_for_update().get(pk=attempt.user_id)
        if not user.is_active:
            raise LoginFailure("account_unavailable")
        if identity and identity.user_id != user.pk:
            raise LoginFailure("identity_in_use")
        if (
            SocialIdentity.objects.filter(user=user, provider=provider)
            .exclude(subject=claims["sub"])
            .exists()
        ):
            raise LoginFailure("already_linked")
        if not identity:
            SocialIdentity.objects.create(user=user, provider=provider, subject=claims["sub"])
        return user
    if identity:
        if not identity.user.is_active:
            raise LoginFailure("account_unavailable")
        return identity.user
    if not claims.get("email"):
        raise LoginFailure("email_required")
    email = claims["email"].strip().lower()
    if User.objects.filter(email__iexact=email).exists():
        # Email alone never proves ownership of an existing shop account.
        raise LoginFailure("email_exists")
    name = str(claims.get("name") or email)[:150]
    user = User.objects.create_user(email=email, password=None, full_name=name)
    Customer.objects.create(user=user, name=name, email=email)
    SocialIdentity.objects.create(user=user, provider=provider, subject=claims["sub"])
    return user


def frontend_redirect(path, query):
    response = HttpResponseRedirect(path + "?" + urlencode(query))
    response["Referrer-Policy"] = "no-referrer"
    return response


@method_decorator(never_cache, name="dispatch")
class GoogleCallbackView(APIView):
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "auth"

    @extend_schema(exclude=True)
    def get(self, request):
        attempt = None
        try:
            if not google_ready():
                raise LoginFailure("not_configured")
            attempt = claim_attempt(request)
            if request.GET.get("error"):
                raise LoginFailure("cancelled")
            code = request.GET.get("code", "")
            if not code or len(code) > 4096:
                raise LoginFailure("verification_failed")
            claims = exchange_and_verify(code, attempt)
            user = account_for(claims, attempt)
            login(request, user, backend="django.contrib.auth.backends.ModelBackend")
            audit(
                user,
                "account.google_linked" if attempt.link_account else "account.google_login",
                user,
            )
            return frontend_redirect(
                "/auth/google/complete",
                {
                    "next": safe_next(attempt.next_path),
                    "linked": "1" if attempt.link_account else "0",
                },
            )
        except LoginFailure as exc:
            error = str(exc)
        except requests.RequestException, GoogleAuthError, ValueError, ValidationError:
            error = "verification_failed"
        except IntegrityError, User.DoesNotExist:
            error = "account_unavailable"
        return frontend_redirect(
            "/profile" if attempt and attempt.link_account else "/login",
            {"google_error": error, "next": safe_next(attempt.next_path) if attempt else ""},
        )
