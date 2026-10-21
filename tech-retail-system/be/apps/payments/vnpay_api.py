import logging
import re
from urllib.parse import urlencode

from django.http import Http404, HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views.decorators.cache import never_cache
from drf_spectacular.utils import extend_schema
from rest_framework import serializers
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from apps.orders.models import Order
from .models import VnpayAttempt
from .vnpay import (
    check_attempt,
    create_attempt,
    ipn_result,
    public_attempt,
    receive_ipn,
    verified_query,
)

NOT_FOUND = "Không tìm thấy thanh toán của tài khoản này. Hãy đăng nhập tài khoản đã đặt đơn."


def owned_attempt(request, reference):
    if not re.fullmatch(r"[0-9a-f]{32}", reference):
        raise Http404(NOT_FOUND)
    attempt = (
        VnpayAttempt.objects.select_related("order")
        .filter(pk=reference, order__customer__user=request.user)
        .first()
    )
    if not attempt:
        raise Http404(NOT_FOUND)
    return attempt


def status_data(attempt):
    data = public_attempt(attempt)
    data["order_payment_status"] = attempt.order.payment_status
    data["payment_url"] = (
        attempt.payment_url
        if (
            attempt.status == "PENDING"
            and attempt.expires_at > timezone.now()
            and attempt.order.payment_status == "UNPAID"
            and attempt.order.status != "CANCELLED"
        )
        else None
    )
    return data


class VnpayInput(serializers.Serializer):
    bank_mode = serializers.ChoiceField(choices=["VNPAYQR", ""], default="", allow_blank=True)


class VnpayResponse(serializers.Serializer):
    reference = serializers.CharField()
    order = serializers.IntegerField()
    amount = serializers.DecimalField(max_digits=18, decimal_places=2)
    status = serializers.CharField()
    expires_at = serializers.DateTimeField()
    payment_url = serializers.URLField(required=False, allow_null=True)
    response_code = serializers.CharField()
    provider_transaction = serializers.CharField(allow_null=True)
    review_reason = serializers.CharField()
    bank_mode = serializers.CharField()
    promotion_code = serializers.CharField()
    promotion_amount = serializers.DecimalField(max_digits=18, decimal_places=2)
    customer_amount = serializers.DecimalField(max_digits=18, decimal_places=2)
    order_payment_status = serializers.CharField(required=False)


@method_decorator(never_cache, name="dispatch")
class VnpayStartView(APIView):
    permission_classes = [IsAuthenticated]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "payment"

    @extend_schema(request=VnpayInput, responses=VnpayResponse)
    def post(self, request, order_id):
        order = get_object_or_404(Order, pk=order_id, customer__user=request.user)
        data = VnpayInput(data=request.data)
        data.is_valid(raise_exception=True)
        attempt = create_attempt(
            order.pk,
            request.user,
            data.validated_data["bank_mode"],
            request.META.get("REMOTE_ADDR", ""),
        )
        return Response(public_attempt(attempt, include_url=True))


@method_decorator(never_cache, name="dispatch")
class VnpayStatusView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(responses=VnpayResponse)
    def get(self, request, reference):
        return Response(status_data(owned_attempt(request, reference)))


@method_decorator(never_cache, name="dispatch")
class VnpayCheckView(APIView):
    permission_classes = [IsAuthenticated]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "payment"

    @extend_schema(request=None, responses=VnpayResponse)
    def post(self, request, reference):
        attempt = check_attempt(owned_attempt(request, reference))
        return Response(status_data(attempt))


@method_decorator(never_cache, name="dispatch")
class VnpayIpnView(APIView):
    authentication_classes = []
    throttle_classes = []

    @extend_schema(exclude=True)
    def get(self, request):
        try:
            return Response(receive_ipn(request.query_params))
        except Exception as exc:
            logging.getLogger("tech_retail.api").error(
                "VNPay IPN handler failed type=%s", type(exc).__name__
            )
            return Response(ipn_result("99"))


@method_decorator(never_cache, name="dispatch")
class VnpayReturnView(APIView):
    authentication_classes = []

    @extend_schema(exclude=True)
    def get(self, request):
        # Browser return is informational; IPN or server QueryDR must verify the payment.
        data = verified_query(request.query_params)
        ref = data.get("vnp_TxnRef", "") if data else ""
        query = {"reference": ref} if re.fullmatch(r"[0-9a-f]{32}", ref) else {"invalid": "1"}
        response = HttpResponseRedirect("/payments/vnpay/return?" + urlencode(query))
        response["Referrer-Policy"] = "no-referrer"
        return response
