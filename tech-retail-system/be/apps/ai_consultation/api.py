from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import serializers
from drf_spectacular.utils import extend_schema
from common.schema import FeatureSerializer, ErrorSerializer
from apps.products.api import VariantSerializer
from .services import retrieve, DisabledProvider


class RetrievalResponseSerializer(serializers.Serializer):
    results = VariantSerializer(many=True)


class FeatureView(APIView):
    @extend_schema(responses=FeatureSerializer)
    def get(self, request):
        return Response(
            {
                "google_login": False,
                "facebook_login": False,
                "gemini": False,
                "ai_status": "DEFERRED",
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
