"""Moderated product reviews and Q&A. No demo content or customer identifiers are published."""

from io import BytesIO
import warnings

from PIL import Image, ImageOps, UnidentifiedImageError
from django.db import transaction
from django.db.models import Avg, Count, Exists, OuterRef, Q, Prefetch
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.utils.decorators import method_decorator
from django.views.decorators.cache import never_cache
from rest_framework import serializers
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView
from drf_spectacular.utils import extend_schema

from apps.accounts.models import User
from apps.accounts.permissions import is_admin, require
from apps.orders.models import Order
from common.audit import audit
from common.errors import BusinessError
from common.pagination import StandardPagination
from .models import (
    Product,
    ProductFeedback,
    FeedbackPhoto,
    FeedbackReply,
    FeedbackVote,
    FeedbackReport,
)


def public_product(slug):
    return get_object_or_404(
        Product, slug=slug, is_active=True, category__is_active=True, brand__is_active=True
    )


def verified_purchase(product, user):
    return (
        Order.objects.filter(
            customer__user=user,
            status="COMPLETED",
            payment_status="PAID",
            items__variant__product=product,
        )
        .order_by("pk")
        .first()
    )


def name(user):
    return user.full_name.strip() or "Khách hàng"


def serialize_reply(reply):
    return {
        "id": reply.pk,
        "author": "TechRetail" if reply.is_staff_reply else name(reply.author),
        "body": reply.body,
        "is_staff_reply": reply.is_staff_reply,
        "status": reply.status,
        "created_at": reply.created_at,
    }


def serialize_feedback(item, user, internal=False):
    owner = user.is_authenticated and item.author_id == user.pk
    replies = [
        r
        for r in item.replies.all()
        if internal or r.status == "APPROVED" or (user.is_authenticated and r.author_id == user.pk)
    ]
    result = {
        "id": item.pk,
        "kind": item.kind,
        "title": item.title,
        "body": item.body,
        "rating": item.rating,
        "status": item.status,
        "author": name(item.author),
        "is_mine": owner,
        "verified_purchase": bool(item.verified_order_id),
        "created_at": item.created_at,
        "photos": [f"/api/v1/feedback/photos/{p.pk}/" for p in item.photos.all()],
        "helpful_count": item.votes.count(),
        "helpful": user.is_authenticated and item.votes.filter(user=user).exists(),
        "replies": [serialize_reply(r) for r in replies],
    }
    if internal:
        result.update(
            product_name=item.product.name,
            product_slug=item.product.slug,
            reports=[{"reason": r.reason, "created_at": r.created_at} for r in item.reports.all()],
        )
    return result


def clean_photo(upload):
    if upload.size > 5 * 1024 * 1024:
        raise serializers.ValidationError({"photos": "Mỗi ảnh tối đa 5 MB."})
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(upload) as image:
                if (
                    image.format not in {"JPEG", "PNG", "WEBP"}
                    or image.width * image.height > 16000000
                ):
                    raise ValueError()
                image.load()
                image = ImageOps.exif_transpose(image).convert("RGB")
                image.thumbnail((1200, 1200))
                out = BytesIO()
                image.save(out, format="JPEG", quality=82)
                return out.getvalue()
    except (
        OSError,
        ValueError,
        UnidentifiedImageError,
        Image.DecompressionBombError,
        Image.DecompressionBombWarning,
    ):
        raise serializers.ValidationError(
            {"photos": "Chỉ nhận ảnh JPG, PNG hoặc WebP hợp lệ, tối đa 16 megapixel."}
        )


class FeedbackInput(serializers.Serializer):
    kind = serializers.ChoiceField(choices=["REVIEW", "QUESTION"])
    title = serializers.CharField(max_length=150, required=False, allow_blank=True, default="")
    body = serializers.CharField(max_length=3000, min_length=5)
    rating = serializers.IntegerField(min_value=1, max_value=5, required=False)
    photos = serializers.ListField(child=serializers.FileField(), max_length=5, required=False)


class TextInput(serializers.Serializer):
    body = serializers.CharField(max_length=3000, min_length=2)


class ModerationInput(serializers.Serializer):
    status = serializers.ChoiceField(choices=["PENDING", "APPROVED", "HIDDEN"])


class VoteInput(serializers.Serializer):
    helpful = serializers.BooleanField()


class ReportInput(serializers.Serializer):
    reason = serializers.CharField(max_length=500, min_length=5)


class ReplyOutput(serializers.Serializer):
    id = serializers.IntegerField()
    author = serializers.CharField()
    body = serializers.CharField()
    is_staff_reply = serializers.BooleanField()
    status = serializers.CharField()
    created_at = serializers.DateTimeField()


class FeedbackOutput(serializers.Serializer):
    id = serializers.IntegerField()
    kind = serializers.CharField()
    title = serializers.CharField()
    body = serializers.CharField()
    rating = serializers.IntegerField(allow_null=True)
    status = serializers.CharField()
    author = serializers.CharField()
    is_mine = serializers.BooleanField()
    verified_purchase = serializers.BooleanField()
    created_at = serializers.DateTimeField()
    photos = serializers.ListField(child=serializers.CharField())
    helpful_count = serializers.IntegerField()
    helpful = serializers.BooleanField()
    replies = ReplyOutput(many=True)
    product_name = serializers.CharField(required=False)
    product_slug = serializers.CharField(required=False)
    reports = serializers.ListField(child=serializers.DictField(), required=False)


class SummaryOutput(serializers.Serializer):
    count = serializers.IntegerField()
    average = serializers.FloatField(allow_null=True)
    distribution = serializers.DictField(child=serializers.IntegerField())
    questions = serializers.IntegerField()


class ViewerOutput(serializers.Serializer):
    can_review = serializers.BooleanField()
    review_status = serializers.CharField(allow_null=True)
    authenticated = serializers.BooleanField()


class FeedbackPageOutput(serializers.Serializer):
    count = serializers.IntegerField()
    next = serializers.URLField(allow_null=True)
    previous = serializers.URLField(allow_null=True)
    results = FeedbackOutput(many=True)
    summary = SummaryOutput(required=False)
    viewer = ViewerOutput(required=False)


class VoteOutput(serializers.Serializer):
    helpful_count = serializers.IntegerField()


class ModerationOutput(serializers.Serializer):
    id = serializers.IntegerField()
    status = serializers.CharField()


class ReportOutput(serializers.Serializer):
    message = serializers.CharField()


@method_decorator(never_cache, name="dispatch")
class ProductFeedbackView(APIView):
    @extend_schema(responses=FeedbackPageOutput)
    def get(self, request, slug):
        product = public_product(slug)
        approved = ProductFeedback.objects.filter(product=product, status="APPROVED")
        reviews = approved.filter(kind="REVIEW")
        stats = reviews.aggregate(count=Count("id"), average=Avg("rating"))
        stats["average"] = round(stats["average"], 1) if stats["average"] is not None else None
        stats["distribution"] = {str(n): reviews.filter(rating=n).count() for n in range(1, 6)}
        stats["questions"] = approved.filter(kind="QUESTION").count()
        mine = None
        eligible = False
        if request.user.is_authenticated:
            mine = ProductFeedback.objects.filter(
                product=product, author=request.user, kind="REVIEW"
            ).first()
            eligible = not mine and bool(verified_purchase(product, request.user))
        kind = request.query_params.get("kind", "REVIEW")
        if kind not in {"REVIEW", "QUESTION"}:
            raise serializers.ValidationError({"kind": "Loại nội dung không hợp lệ."})
        qs = ProductFeedback.objects.filter(product=product, kind=kind)
        visibility = Q(status="APPROVED")
        if request.user.is_authenticated:
            visibility |= Q(author=request.user)
        qs = qs.filter(visibility)
        rating = request.query_params.get("rating")
        if rating:
            if rating not in {"1", "2", "3", "4", "5"}:
                raise serializers.ValidationError({"rating": "Số sao không hợp lệ."})
            qs = qs.filter(rating=int(rating))
        if request.query_params.get("photos") == "true":
            qs = qs.filter(Exists(FeedbackPhoto.objects.filter(feedback_id=OuterRef("pk"))))
        if request.query_params.get("answered") in {"true", "false"}:
            qs = qs.annotate(
                answered=Exists(
                    FeedbackReply.objects.filter(
                        feedback_id=OuterRef("pk"), status="APPROVED", is_staff_reply=True
                    )
                )
            )
            qs = qs.filter(answered=request.query_params["answered"] == "true")
        search = request.query_params.get("search", "").strip()[:200]
        if search:
            qs = qs.filter(Q(body__icontains=search) | Q(title__icontains=search))
        qs = qs.select_related("author").prefetch_related(
            Prefetch("photos", queryset=FeedbackPhoto.objects.only("id", "feedback_id")),
            "replies__author",
        )
        if request.query_params.get("sort") == "helpful":
            qs = qs.annotate(vote_total=Count("votes")).order_by("-vote_total", "-id")
        pager = StandardPagination()
        rows = pager.paginate_queryset(qs, request)
        response = pager.get_paginated_response(
            [serialize_feedback(item, request.user) for item in rows]
        )
        response.data.update(
            summary=stats,
            viewer={
                "can_review": bool(eligible),
                "review_status": mine.status if mine else None,
                "authenticated": request.user.is_authenticated,
            },
        )
        return response

    @extend_schema(request=FeedbackInput, responses={201: FeedbackOutput})
    def post(self, request, slug):
        if not request.user.is_authenticated:
            raise PermissionDenied("Vui lòng đăng nhập để gửi nội dung.")
        FeedbackWriteThrottle().allow_or_raise(request, self)
        product = public_product(slug)
        data = FeedbackInput(data=request.data)
        data.is_valid(raise_exception=True)
        values = data.validated_data
        photos = [clean_photo(photo) for photo in values.pop("photos", [])]
        kind = values["kind"]
        if kind == "QUESTION" and (photos or "rating" in values):
            raise serializers.ValidationError("Hỏi đáp không có điểm sao hoặc ảnh đánh giá.")
        if kind == "REVIEW" and "rating" not in values:
            raise serializers.ValidationError({"rating": "Vui lòng chọn số sao."})
        with transaction.atomic():
            User.objects.select_for_update().get(pk=request.user.pk)
            purchase = None
            if kind == "REVIEW":
                if ProductFeedback.objects.filter(
                    product=product, author=request.user, kind=kind
                ).exists():
                    raise BusinessError("Bạn đã gửi đánh giá cho sản phẩm này.", "REVIEW_EXISTS")
                purchase = verified_purchase(product, request.user)
                if not purchase:
                    raise PermissionDenied(
                        "Chỉ khách có đơn đã hoàn tất và thanh toán mới được đánh giá."
                    )
            item = ProductFeedback.objects.create(
                product=product,
                author=request.user,
                verified_order=purchase,
                review_identity=f"{product.pk}:{request.user.pk}" if purchase else None,
                **values,
            )
            FeedbackPhoto.objects.bulk_create(
                [FeedbackPhoto(feedback=item, content=photo) for photo in photos]
            )
            audit(request.user, "feedback.submit", item, kind=kind)
        return Response(serialize_feedback(item, request.user), status=201)


class FeedbackWriteThrottle(ScopedRateThrottle):
    scope = "feedback"

    def allow_or_raise(self, request, view):
        from rest_framework.exceptions import Throttled

        self.scope = "feedback"
        # ScopedRateThrottle reads the scope off the view.
        view.throttle_scope = self.scope
        if not self.allow_request(request, view):
            raise Throttled(self.wait())


def visible_item(request, pk):
    qs = ProductFeedback.objects.filter(
        product__is_active=True, product__category__is_active=True, product__brand__is_active=True
    )
    if not is_admin(request.user):
        qs = qs.filter(status="APPROVED")
    return get_object_or_404(qs, pk=pk)


class FeedbackReplyView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(request=TextInput, responses={201: ReplyOutput})
    def post(self, request, pk):
        FeedbackWriteThrottle().allow_or_raise(request, self)
        data = TextInput(data=request.data)
        data.is_valid(raise_exception=True)
        with transaction.atomic():
            item = visible_item(request, pk)
            staff = is_admin(request.user)
            if item.kind == "REVIEW" and not staff:
                raise PermissionDenied("Chỉ quản trị viên được phản hồi đánh giá.")
            reply = FeedbackReply.objects.create(
                feedback=item,
                author=request.user,
                is_staff_reply=staff,
                status="APPROVED" if staff else "PENDING",
                **data.validated_data,
            )
            audit(request.user, "feedback.reply", reply, feedback=item.pk, staff=staff)
        return Response(serialize_reply(reply), status=201)


class FeedbackVoteView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(request=VoteInput, responses=VoteOutput)
    def put(self, request, pk):
        item = visible_item(request, pk)
        data = VoteInput(data=request.data)
        data.is_valid(raise_exception=True)
        if data.validated_data["helpful"]:
            FeedbackVote.objects.get_or_create(feedback=item, user=request.user)
        else:
            FeedbackVote.objects.filter(feedback=item, user=request.user).delete()
        return Response({"helpful_count": item.votes.count()})


class FeedbackReportView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(request=ReportInput, responses=ReportOutput)
    def post(self, request, pk):
        FeedbackWriteThrottle().allow_or_raise(request, self)
        item = visible_item(request, pk)
        data = ReportInput(data=request.data)
        data.is_valid(raise_exception=True)
        FeedbackReport.objects.update_or_create(
            feedback=item, user=request.user, defaults=data.validated_data
        )
        return Response({"message": "Đã gửi báo cáo đến quản trị viên."})


@method_decorator(never_cache, name="dispatch")
class FeedbackPhotoView(APIView):
    @extend_schema(responses={(200, "image/jpeg"): bytes})
    def get(self, request, pk):
        photo = get_object_or_404(FeedbackPhoto.objects.select_related("feedback__product"), pk=pk)
        item = photo.feedback
        if not (
            is_admin(request.user)
            or (request.user.is_authenticated and item.author_id == request.user.pk)
        ):
            get_object_or_404(
                ProductFeedback,
                pk=item.pk,
                status="APPROVED",
                product__is_active=True,
                product__category__is_active=True,
                product__brand__is_active=True,
            )
        response = HttpResponse(bytes(photo.content), content_type="image/jpeg")
        response["X-Content-Type-Options"] = "nosniff"
        return response


@method_decorator(never_cache, name="dispatch")
class FeedbackAdminView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(responses=FeedbackPageOutput)
    def get(self, request):
        require(request.user, "manage_accounts")
        qs = ProductFeedback.objects.select_related("product", "author").prefetch_related(
            Prefetch("photos", queryset=FeedbackPhoto.objects.only("id", "feedback_id")),
            "replies__author",
            "reports",
        )
        for field in ["kind", "status"]:
            if request.query_params.get(field):
                if field == "status" and request.query_params[field] == "PENDING":
                    qs = qs.annotate(
                        pending_reply=Exists(
                            FeedbackReply.objects.filter(
                                feedback_id=OuterRef("pk"), status="PENDING"
                            )
                        )
                    ).filter(Q(status="PENDING") | Q(pending_reply=True))
                else:
                    qs = qs.filter(**{field: request.query_params[field]})
        if request.query_params.get("reported") == "true":
            qs = qs.filter(Exists(FeedbackReport.objects.filter(feedback_id=OuterRef("pk"))))
        search = request.query_params.get("search", "").strip()[:200]
        if search:
            qs = qs.filter(Q(product__name__icontains=search) | Q(body__icontains=search))
        pager = StandardPagination()
        rows = pager.paginate_queryset(qs, request)
        return pager.get_paginated_response(
            [serialize_feedback(item, request.user, True) for item in rows]
        )


class FeedbackModerateView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(request=ModerationInput, responses=ModerationOutput)
    def patch(self, request, pk, reply=False):
        require(request.user, "manage_accounts")
        data = ModerationInput(data=request.data)
        data.is_valid(raise_exception=True)
        with transaction.atomic():
            item = get_object_or_404(
                (FeedbackReply if reply else ProductFeedback).objects.select_for_update(), pk=pk
            )
            before = item.status
            item.status = data.validated_data["status"]
            item.save(update_fields=["status", "updated_at"])
            audit(request.user, "feedback.moderate", item, before=before, after=item.status)
        return Response({"id": item.pk, "status": item.status})
