"""Facebook server-side code flow. Provider tokens never leave this module."""

import hashlib
import hmac
import re
import secrets
import time
from datetime import timedelta
from urllib.parse import urlencode, urlsplit

import requests
from django.conf import settings
from django.contrib.auth import login
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.db import IntegrityError, transaction
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views.decorators.cache import never_cache
from django.views.decorators.debug import sensitive_variables
from drf_spectacular.utils import extend_schema
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from common.audit import audit
from common.errors import BusinessError
from .google_login import (
    LoginFailure,
    StartInput,
    StartResponse,
    account_for,
    digest,
    frontend_redirect,
    safe_next,
)
from .models import FacebookLoginAttempt, User

CALLBACK_PATH = "/api/v1/auth/facebook/callback/"


def facebook_ready():
    return bool(
        settings.FACEBOOK_LOGIN_ENABLED
        and settings.FACEBOOK_APP_ID
        and settings.FACEBOOK_APP_SECRET
        and settings.FACEBOOK_REDIRECT_URI
        and re.fullmatch(r"v\d+\.\d+", settings.FACEBOOK_GRAPH_VERSION)
    )


def callback_for(request):
    uri = settings.FACEBOOK_REDIRECT_URI
    parsed = urlsplit(uri)
    # Exact originating host preserves state cookies; never redirect the callback to another host.
    if (
        parsed.scheme in ("http", "https")
        and (
            parsed.scheme == "https"
            or (settings.APP_ENV != "production" and parsed.hostname in ("localhost", "127.0.0.1"))
        )
        and not parsed.username
        and not parsed.password
        and not parsed.query
        and not parsed.fragment
        and parsed.path == CALLBACK_PATH
        and request.build_absolute_uri(CALLBACK_PATH) == uri
    ):
        return uri
    raise BusinessError(
        "Địa chỉ web không khớp callback Facebook. Vui lòng mở đúng địa chỉ FACEBOOK_REDIRECT_URI.",
        "FACEBOOK_CALLBACK_NOT_CONFIGURED",
        503,
    )


@method_decorator(never_cache, name="dispatch")
class FacebookStartView(APIView):
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "auth"

    @extend_schema(request=StartInput, responses=StartResponse)
    def post(self, request):
        if not facebook_ready():
            raise BusinessError(
                "Đăng nhập Facebook chưa được cấu hình.", "FACEBOOK_NOT_CONFIGURED", 503
            )
        data = StartInput(data=request.data)
        data.is_valid(raise_exception=True)
        link_account = data.validated_data["link_account"]
        if link_account and not request.user.is_authenticated:
            raise BusinessError("Đăng nhập trước khi liên kết Facebook.", "AUTH_REQUIRED", 403)
        uri = callback_for(request)
        if not request.session.session_key:
            request.session.create()
        state = secrets.token_urlsafe(48)
        FacebookLoginAttempt.objects.create(
            state_hash=digest(state),
            session_hash=digest(request.session.session_key),
            redirect_uri=uri,
            link_account=link_account,
            user=request.user if request.user.is_authenticated else None,
            next_path="/profile"
            if link_account
            else safe_next(data.validated_data.get("next", "")),
            expires_at=timezone.now() + timedelta(minutes=5),
        )
        query = urlencode(
            {
                "client_id": settings.FACEBOOK_APP_ID,
                "redirect_uri": uri,
                "response_type": "code",
                "scope": "public_profile,email",
                "state": state,
            }
        )
        return Response(
            {
                "authorization_url": f"https://www.facebook.com/{settings.FACEBOOK_GRAPH_VERSION}/dialog/oauth?{query}"
            }
        )


def claim_attempt(request):
    state = request.GET.get("state", "")
    if not state or len(state) > 256 or not request.session.session_key:
        raise LoginFailure("invalid_state")
    with transaction.atomic():
        attempt = (
            FacebookLoginAttempt.objects.select_for_update()
            .filter(state_hash=digest(state))
            .first()
        )
        if (
            not attempt
            or attempt.used_at
            or attempt.expires_at <= timezone.now()
            or not secrets.compare_digest(attempt.session_hash, digest(request.session.session_key))
            or attempt.user_id != (request.user.pk if request.user.is_authenticated else None)
            or request.build_absolute_uri(CALLBACK_PATH) != attempt.redirect_uri
            or attempt.redirect_uri != settings.FACEBOOK_REDIRECT_URI
        ):
            raise LoginFailure("invalid_state")
        FacebookLoginAttempt.objects.filter(pk=attempt.pk).update(used_at=timezone.now())
    return attempt


def response_json(response):
    if response.status_code != 200:
        raise LoginFailure("verification_failed")
    value = response.json()
    if not isinstance(value, dict) or "error" in value:
        raise LoginFailure("verification_failed")
    return value


@sensitive_variables()
def exchange_and_verify(code, attempt):
    base = f"https://graph.facebook.com/{settings.FACEBOOK_GRAPH_VERSION}"
    options = {"timeout": (3.05, 10), "allow_redirects": False}
    with requests.Session() as http:
        payload = response_json(
            http.get(
                base + "/oauth/access_token",
                params={
                    "client_id": settings.FACEBOOK_APP_ID,
                    "client_secret": settings.FACEBOOK_APP_SECRET,
                    "redirect_uri": attempt.redirect_uri,
                    "code": code,
                },
                **options,
            )
        )
        token = payload.get("access_token")
        if not isinstance(token, str) or not 0 < len(token) <= 20000:
            raise LoginFailure("verification_failed")
        debug = response_json(
            http.get(
                base + "/debug_token",
                params={"input_token": token},
                headers={
                    "Authorization": f"Bearer {settings.FACEBOOK_APP_ID}|{settings.FACEBOOK_APP_SECRET}"
                },
                **options,
            )
        ).get("data")
        if (
            not isinstance(debug, dict)
            or debug.get("is_valid") is not True
            or str(debug.get("app_id")) != settings.FACEBOOK_APP_ID
            or debug.get("type") != "USER"
            or not isinstance(debug.get("user_id"), str)
            or not re.fullmatch(r"[0-9]{1,255}", debug["user_id"])
            or not isinstance(debug.get("expires_at"), (int, float))
            or debug["expires_at"] <= time.time()
            or (
                debug.get("data_access_expires_at")
                and debug["data_access_expires_at"] <= time.time()
            )
        ):
            raise LoginFailure("verification_failed")
        proof = hmac.new(
            settings.FACEBOOK_APP_SECRET.encode(), token.encode(), hashlib.sha256
        ).hexdigest()
        profile = response_json(
            http.get(
                base + "/me",
                params={"fields": "id,name,email", "appsecret_proof": proof},
                headers={"Authorization": "Bearer " + token},
                **options,
            )
        )
    if profile.get("id") != debug["user_id"]:
        raise LoginFailure("verification_failed")
    email = profile.get("email")
    if email is not None:
        if not isinstance(email, str) or len(email) > 254:
            raise LoginFailure("verification_failed")
        validate_email(email)
    return {"sub": profile["id"], "name": profile.get("name"), "email": email}


@method_decorator(never_cache, name="dispatch")
class FacebookCallbackView(APIView):
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "auth"

    @extend_schema(exclude=True)
    def get(self, request):
        attempt = None
        try:
            if not facebook_ready():
                raise LoginFailure("not_configured")
            attempt = claim_attempt(request)
            if request.GET.get("error"):
                raise LoginFailure("cancelled")
            code = request.GET.get("code", "")
            if not code or len(code) > 4096:
                raise LoginFailure("verification_failed")
            claims = exchange_and_verify(code, attempt)
            user = account_for(claims, attempt, provider="facebook")
            login(request, user, backend="django.contrib.auth.backends.ModelBackend")
            audit(
                user,
                "account.facebook_linked" if attempt.link_account else "account.facebook_login",
                user,
            )
            return frontend_redirect(
                "/auth/facebook/complete",
                {
                    "next": safe_next(attempt.next_path),
                    "linked": "1" if attempt.link_account else "0",
                },
            )
        except LoginFailure as exc:
            error = str(exc)
        except requests.RequestException, ValueError, TypeError, ValidationError:
            error = "verification_failed"
        except IntegrityError, User.DoesNotExist:
            error = "account_unavailable"
        return frontend_redirect(
            "/profile" if attempt and attempt.link_account else "/login",
            {
                "facebook_error": error,
                "next": safe_next(attempt.next_path) if attempt else "",
            },
        )
