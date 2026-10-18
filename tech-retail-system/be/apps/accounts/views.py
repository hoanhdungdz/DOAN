import hashlib
import secrets
from datetime import timedelta
from django.conf import settings
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from django.core.mail import send_mail
from django.db import transaction
from django.middleware.csrf import get_token
from django.utils import timezone
from rest_framework import serializers
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.throttling import ScopedRateThrottle
from drf_spectacular.utils import extend_schema, extend_schema_view
from common.schema import AuthInputSerializer, SessionResponseSerializer
from common.errors import BusinessError
from common.audit import audit
from apps.customers.models import Customer
from .models import User, ResetChallenge
from .permissions import capabilities, store_ids, is_admin


def user_payload(user):
    return {
        "id": user.pk,
        "email": user.email,
        "full_name": user.full_name,
        "is_admin": is_admin(user),
        "permissions": capabilities(user),
        "stores": store_ids(user),
    }


def password_check(value, user=None):
    try:
        validate_password(value, user)
    except DjangoValidationError as exc:
        raise serializers.ValidationError({"password": exc.messages})


class Credentials(serializers.Serializer):
    email = serializers.EmailField(max_length=254)
    password = serializers.CharField(max_length=128, write_only=True)
    full_name = serializers.CharField(max_length=150, required=False, allow_blank=True)


class CsrfView(APIView):
    @extend_schema(responses=SessionResponseSerializer)
    def get(self, request):
        return Response({"csrfToken": get_token(request)})


class AuthView(APIView):
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "auth"

    @extend_schema(
        request=AuthInputSerializer,
        responses=SessionResponseSerializer,
        description="action: register/login/logout/forgot-password/reset-password/change-password. See API.md for required fields by action; CSRF required for every POST.",
    )
    def post(self, request, action):
        if action in ("register", "login"):
            s = Credentials(data=request.data)
            s.is_valid(raise_exception=True)
            d = s.validated_data
            email = d["email"].strip().lower()
            if action == "register":
                password_check(d["password"], User(email=email))
                with transaction.atomic():
                    if User.objects.filter(email=email).exists():
                        raise serializers.ValidationError({"email": "Email đã được sử dụng."})
                    user = User.objects.create_user(
                        email, d["password"], full_name=d.get("full_name", "")
                    )
                    Customer.objects.create(user=user, name=user.full_name or email, email=email)
            else:
                user = authenticate(request, email=email, password=d["password"])
                if not user:
                    raise BusinessError(
                        "Email hoặc mật khẩu không đúng.", "INVALID_CREDENTIALS", 400
                    )
            login(request, user)
            return Response({"user": user_payload(user), "csrfToken": get_token(request)})
        if action == "logout":
            logout(request)
            return Response({"message": "Đã đăng xuất.", "csrfToken": get_token(request)})
        if action == "forgot-password":
            s = type("EmailInput", (serializers.Serializer,), {"email": serializers.EmailField()})(
                data=request.data
            )
            s.is_valid(raise_exception=True)
            user = User.objects.filter(
                email=s.validated_data["email"].strip().lower(), is_active=True
            ).first()
            if user:
                # Per-account cooldown independent of IP enumeration protection.
                with transaction.atomic():
                    User.objects.select_for_update().get(pk=user.pk)
                    if not ResetChallenge.objects.filter(
                        user=user, created_at__gte=timezone.now() - timedelta(seconds=60)
                    ).exists():
                        token = secrets.token_urlsafe(32)
                        ResetChallenge.objects.create(
                            user=user,
                            token_hash=hashlib.sha256(token.encode()).hexdigest(),
                            expires_at=timezone.now()
                            + timedelta(seconds=settings.PASSWORD_RESET_TIMEOUT),
                        )
                        link = settings.CUSTOMER_FRONTEND_URL + "/reset-password?token=" + token
                        transaction.on_commit(
                            lambda: send_mail(
                                "Đặt lại mật khẩu Tech Retail",
                                "Link đặt lại mật khẩu (1 giờ, dùng một lần): " + link,
                                settings.DEFAULT_FROM_EMAIL,
                                [user.email],
                            )
                        )
            return Response(
                {
                    "message": "Nếu tài khoản phù hợp, hướng dẫn đặt lại mật khẩu sẽ được gửi qua email.",
                    "delivery_mode": settings.EMAIL_DELIVERY_MODE,
                }
            )
        if action == "reset-password":
            token = request.data.get("token", "")
            password = request.data.get("password", "")
            if not isinstance(token, str) or len(token) > 200 or not isinstance(password, str):
                raise serializers.ValidationError("Dữ liệu không hợp lệ.")
            with transaction.atomic():
                challenge = (
                    ResetChallenge.objects.select_for_update()
                    .select_related("user")
                    .filter(
                        token_hash=hashlib.sha256(token.encode()).hexdigest(),
                        used_at__isnull=True,
                        expires_at__gt=timezone.now(),
                        user__is_active=True,
                    )
                    .first()
                )
                if not challenge:
                    raise BusinessError(
                        "Link không hợp lệ hoặc đã hết hạn.", "INVALID_RESET_TOKEN", 400
                    )
                password_check(password, challenge.user)
                challenge.user.set_password(password)
                challenge.user.save()
                challenge.used_at = timezone.now()
                challenge.save(update_fields=["used_at"])
            return Response({"message": "Mật khẩu đã được đặt lại. Vui lòng đăng nhập."})
        if action == "change-password":
            if not request.user.is_authenticated:
                raise BusinessError("Cần đăng nhập.", "AUTH_REQUIRED", 403)
            if not request.user.check_password(request.data.get("current_password", "")):
                raise BusinessError("Mật khẩu hiện tại không đúng.", "INVALID_CREDENTIALS", 400)
            password = request.data.get("password", "")
            password_check(password, request.user)
            request.user.set_password(password)
            request.user.save()
            audit(request.user, "account.password_changed", request.user)
            logout(request)
            return Response({"message": "Đã đổi mật khẩu. Vui lòng đăng nhập lại."})
        raise BusinessError("Chức năng không tồn tại.", "NOT_FOUND", 404)


class MeView(APIView):
    @extend_schema(responses=SessionResponseSerializer)
    def get(self, request):
        return Response(
            {"user": user_payload(request.user) if request.user.is_authenticated else None}
        )


class ProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = Customer
        fields = ["name", "phone", "email", "address"]


@extend_schema_view(
    get=extend_schema(responses=ProfileSerializer),
    patch=extend_schema(request=ProfileSerializer, responses=ProfileSerializer),
)
class ProfileView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        c, _ = Customer.objects.get_or_create(
            user=request.user,
            defaults={
                "name": request.user.full_name or request.user.email,
                "email": request.user.email,
            },
        )
        return Response(ProfileSerializer(c).data)

    def patch(self, request):
        c, _ = Customer.objects.get_or_create(
            user=request.user, defaults={"name": request.user.full_name or request.user.email}
        )
        s = ProfileSerializer(c, data=request.data, partial=True)
        s.is_valid(raise_exception=True)
        s.save()
        return Response(s.data)
