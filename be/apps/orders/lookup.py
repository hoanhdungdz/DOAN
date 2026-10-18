import secrets
import uuid
from datetime import timedelta
from django.conf import settings
from django.contrib.auth.hashers import make_password, check_password
from django.db import transaction
from django.utils import timezone
from rest_framework import serializers
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from drf_spectacular.utils import extend_schema, extend_schema_view, PolymorphicProxySerializer
from common.schema import LookupResponseSerializer
from common.errors import BusinessError
from .models import Order, OTPChallenge
from .api import normalize_phone


class DevelopmentSMSAdapter:
    def send(self, phone, code, challenge):
        if settings.APP_ENV == "production" or settings.SMS_DELIVERY_MODE != "development":
            raise BusinessError("Chưa cấu hình SMS provider.", "SMS_NOT_CONFIGURED", 503)
        settings.DEV_INBOX.mkdir(mode=0o700, parents=True, exist_ok=True)
        path = settings.DEV_INBOX / (str(challenge) + ".txt")
        path.write_text(
            f"DEVELOPMENT ONLY — SMS chưa gửi thật\nTo: {phone}\nOTP: {code}\n", encoding="utf-8"
        )
        path.chmod(0o600)


class LookupInput(serializers.Serializer):
    code = serializers.CharField(max_length=30)
    phone = serializers.CharField(max_length=30)

    def validate_phone(self, value):
        return normalize_phone(value)


class VerifyInput(serializers.Serializer):
    challenge = serializers.UUIDField()
    otp = serializers.RegexField(r"^\d{6}$")


@extend_schema_view(
    post=extend_schema(
        request=PolymorphicProxySerializer(
            component_name="LookupPayload",
            serializers=[LookupInput, VerifyInput],
            resource_type_field_name=None,
        ),
        responses=LookupResponseSerializer,
    ),
    get=extend_schema(responses=LookupResponseSerializer),
)
class LookupView(APIView):
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "lookup"

    def post(self, request, action):
        if action == "request":
            s = LookupInput(data=request.data)
            s.is_valid(raise_exception=True)
            d = s.validated_data
            challenge_id = uuid.uuid4()
            with transaction.atomic():
                order = (
                    Order.objects.select_for_update()
                    .filter(code=d["code"], phone=d["phone"])
                    .first()
                )
                if (
                    order
                    and not OTPChallenge.objects.filter(
                        order=order,
                        created_at__gt=timezone.now()
                        - timedelta(seconds=settings.OTP_RESEND_COOLDOWN_SECONDS),
                    ).exists()
                ):
                    otp = f"{secrets.randbelow(1000000):06d}"
                    challenge = OTPChallenge.objects.create(
                        order=order,
                        code_hash=make_password(otp),
                        expires_at=timezone.now() + timedelta(seconds=settings.OTP_TTL_SECONDS),
                    )
                    challenge_id = challenge.pk
                    transaction.on_commit(
                        lambda: DevelopmentSMSAdapter().send(order.phone, otp, challenge.pk)
                    )
            return Response(
                {
                    "challenge": str(challenge_id),
                    "message": "Nếu thông tin phù hợp và đã qua thời gian chờ, mã xác minh sẽ được gửi.",
                    "delivery_mode": settings.SMS_DELIVERY_MODE,
                }
            )
        if action == "verify":
            s = VerifyInput(data=request.data)
            s.is_valid(raise_exception=True)
            d = s.validated_data
            valid = False
            with transaction.atomic():
                challenge = (
                    OTPChallenge.objects.select_for_update().filter(pk=d["challenge"]).first()
                )
                if (
                    challenge
                    and not challenge.used_at
                    and challenge.expires_at > timezone.now()
                    and challenge.attempts < settings.OTP_MAX_ATTEMPTS
                ):
                    challenge.attempts += 1
                    if check_password(d["otp"], challenge.code_hash):
                        challenge.used_at = timezone.now()
                        valid = True
                    challenge.save(update_fields=["attempts", "used_at"])
            if not valid:
                raise BusinessError("Mã xác minh không hợp lệ hoặc đã hết hạn.", "INVALID_OTP", 400)
            request.session["order_lookup"] = {
                "order": challenge.order_id,
                "expires": (timezone.now() + timedelta(minutes=10)).timestamp(),
            }
            return Response({"message": "Đã xác minh.", "expires_in": 600})
        raise BusinessError("Không tìm thấy.", "NOT_FOUND", 404)

    def get(self, request, action):
        grant = request.session.get("order_lookup", {})
        if action != "result" or grant.get("expires", 0) <= timezone.now().timestamp():
            raise BusinessError("Cần xác minh OTP.", "LOOKUP_REQUIRED", 403)
        order = Order.objects.get(pk=grant["order"])
        # Deliberately excludes address, phone, customer identifiers and payment references.
        return Response(
            {
                "code": order.code,
                "status": order.status,
                "payment_status": order.payment_status,
                "grand_total": str(order.grand_total),
                "created_at": order.created_at,
                "items": [
                    {
                        "name": i.name,
                        "sku": i.sku,
                        "quantity": i.quantity,
                        "unit_price": str(i.unit_price),
                    }
                    for i in order.items.all()
                ],
            }
        )
