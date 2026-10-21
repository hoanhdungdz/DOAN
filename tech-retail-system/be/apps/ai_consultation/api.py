from rest_framework.views import APIView
from django.conf import settings
from rest_framework.response import Response
from rest_framework import serializers
from drf_spectacular.utils import extend_schema
from common.schema import FeatureSerializer, ErrorSerializer
from apps.products.api import VariantSerializer
from .services import retrieve, DisabledProvider
from apps.accounts.google_login import google_ready
from apps.accounts.facebook_login import facebook_ready
from apps.payments.vnpay import ready as vnpay_ready


class RetrievalResponseSerializer(serializers.Serializer):
    results = VariantSerializer(many=True)


class FeatureView(APIView):
    @extend_schema(responses=FeatureSerializer)
    def get(self, request):
        return Response(
            {
                "google_login": google_ready(),
                "facebook_login": facebook_ready(),
                "vnpay_sandbox": vnpay_ready(),
                "gemini": False,
                "ai_status": "DEFERRED",
                "customer_frontend_url": settings.CUSTOMER_FRONTEND_URL,
            }
        )


class RetrievalView(APIView):
    @extend_schema(
        responses=RetrievalResponseSerializer,
        description="Database catalog retrieval. Accepts catalog filters; never account/order data.",
    )
    def get(self, request):
        return Response({"results": retrieve(request.query_params, request)})


class ChatInput(serializers.Serializer):
    question = serializers.CharField(max_length=2000)
    history = serializers.ListField(child=serializers.DictField(), max_length=10, required=False)


class ChatView(APIView):
    @extend_schema(request=ChatInput, responses={503: ErrorSerializer})
    def post(self, request):
        s = ChatInput(data=request.data)
        s.is_valid(raise_exception=True)
        return Response(DisabledProvider().consult(s.validated_data["question"], []))
