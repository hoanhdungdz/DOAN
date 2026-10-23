from rest_framework.views import APIView
from django.conf import settings
from rest_framework.response import Response
from rest_framework import serializers
from rest_framework.throttling import ScopedRateThrottle
from drf_spectacular.utils import extend_schema
from common.schema import FeatureSerializer, ErrorSerializer
from apps.products.api import VariantSerializer
from .services import retrieve
from .provider import ready
from .rag import consult
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
                "gemini": ready(),
                "ai_status": "RAG_ENABLED" if ready() else "DISABLED",
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


class HistoryItem(serializers.Serializer):
    question = serializers.CharField(max_length=2000)
    # Backward-compatible input only. Assistant text is never trusted or sent to Gemini.
    answer = serializers.CharField(max_length=6000, required=False, allow_blank=True)


class ChatInput(serializers.Serializer):
    question = serializers.CharField(max_length=2000)
    history = HistoryItem(many=True, max_length=6, required=False)
    product_slug = serializers.SlugField(max_length=250, required=False, allow_blank=True)


class ChatSource(serializers.Serializer):
    id = serializers.CharField()
    title = serializers.CharField()
    excerpt = serializers.CharField()


class ChatProduct(serializers.Serializer):
    id = serializers.IntegerField()
    name = serializers.CharField()
    sku = serializers.CharField()
    path = serializers.CharField()
    image = serializers.CharField(allow_blank=True)
    price = serializers.DecimalField(max_digits=18, decimal_places=2)
    condition = serializers.CharField()
    warranty_months = serializers.IntegerField()
    stock = serializers.ListField(child=serializers.DictField())


class ChatResponse(serializers.Serializer):
    answer = serializers.CharField()
    products = ChatProduct(many=True)
    sources = ChatSource(many=True)
    actions = serializers.ListField(child=serializers.DictField())
    mode = serializers.CharField()
    checked_at = serializers.DateTimeField()


class ChatView(APIView):
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "chat"

    @extend_schema(request=ChatInput, responses={200: ChatResponse, 503: ErrorSerializer})
    def post(self, request):
        s = ChatInput(data=request.data)
        s.is_valid(raise_exception=True)
        response = Response(consult(**s.validated_data))
        response["Cache-Control"] = "no-store"
        return response
