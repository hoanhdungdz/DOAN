from io import BytesIO

from PIL import Image
from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from rest_framework.test import APIClient

from apps.orders.services import create_order
from apps.products.models import (
    ProductFeedback,
    FeedbackReply,
    FeedbackPhoto,
    FeedbackVote,
    FeedbackReport,
)
from .factories import scenario, checkout, assign


def photo():
    stream = BytesIO()
    image = Image.new("RGB", (20, 20), "green")
    exif = Image.Exif()
    exif[270] = "private metadata"
    image.save(stream, "JPEG", exif=exif)
    return SimpleUploadedFile("photo.jpg", stream.getvalue(), content_type="image/jpeg")


class FeedbackTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.s = scenario(quantity=100)
        cls.s["customer"].full_name = "Khách mua thật"
        cls.s["customer"].save()
        cls.order = create_order(checkout(cls.s), cls.s["customer"], "feedback", "fixture")
        cls.order.status = "COMPLETED"
        cls.order.payment_status = "PAID"
        cls.order.save(update_fields=["status", "payment_status"])

    def setUp(self):
        cache.clear()
        self.client = APIClient()
        self.path = f"/api/v1/products/{self.s['p'].slug}/feedback/"

    def login(self, who="customer"):
        self.client.force_authenticate(self.s[who])

    def post(self, **extra):
        self.login()
        return self.client.post(
            self.path,
            {"kind": "REVIEW", "rating": 5, "body": "Sản phẩm rất tốt.", **extra},
            format="json",
        )

    def approved(self, kind="REVIEW"):
        return ProductFeedback.objects.create(
            product=self.s["p"],
            author=self.s["customer"],
            kind=kind,
            rating=5 if kind == "REVIEW" else None,
            body="Nội dung công khai",
            status="APPROVED",
            verified_order=self.order if kind == "REVIEW" else None,
            review_identity=f"{self.s['p'].pk}:{self.s['customer'].pk}"
            if kind == "REVIEW"
            else None,
        )

    def test_empty_product_has_no_demo_reviews_or_invented_rating(self):
        response = self.client.get(self.path)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json()["summary"],
            {
                "count": 0,
                "average": None,
                "distribution": {str(n): 0 for n in range(1, 6)},
                "questions": 0,
            },
        )
        self.assertEqual(response.json()["results"], [])
        self.assertFalse(response.json()["viewer"]["can_review"])

    def test_anonymous_cannot_submit_or_moderate(self):
        self.assertEqual(
            self.client.post(
                self.path, {"kind": "QUESTION", "body": "Có còn hàng không?"}
            ).status_code,
            403,
        )
        self.assertEqual(self.client.get("/api/v1/feedback-admin/").status_code, 403)
        self.assertFalse(ProductFeedback.objects.exists())

    def test_only_own_completed_paid_purchase_grants_review(self):
        self.login("other")
        data = {"kind": "REVIEW", "rating": 5, "body": "Tôi chưa mua sản phẩm."}
        self.assertEqual(self.client.post(self.path, data).status_code, 403)
        self.assertFalse(self.client.get(self.path).json()["viewer"]["can_review"])
        self.order.status = "SHIPPED"
        self.order.save(update_fields=["status"])
        self.assertEqual(self.post().status_code, 403)
        self.order.status = "COMPLETED"
        self.order.payment_status = "REFUNDED"
        self.order.save(update_fields=["status", "payment_status"])
        self.assertEqual(self.post().status_code, 403)

    def test_submit_pending_ignores_forged_author_moderation_and_purchase(self):
        response = self.post(
            status="APPROVED", author=self.s["admin"].pk, verified_order=999, is_staff_reply=True
        )
        self.assertEqual(response.status_code, 201, response.content)
        row = ProductFeedback.objects.get()
        self.assertEqual(row.author, self.s["customer"])
        self.assertEqual(row.verified_order, self.order)
        self.assertEqual(row.status, "PENDING")
        self.assertEqual(self.client.get(self.path).json()["viewer"]["review_status"], "PENDING")

    def test_review_cannot_be_duplicated_even_after_hiding(self):
        self.assertEqual(self.post().status_code, 201)
        ProductFeedback.objects.update(status="HIDDEN")
        self.assertEqual(self.post().status_code, 409)
        self.assertEqual(ProductFeedback.objects.count(), 1)

    def test_pending_visible_only_to_author_and_never_in_public_average(self):
        self.post()
        self.assertEqual(self.client.get(self.path).json()["count"], 1)
        self.assertIsNone(self.client.get(self.path).json()["summary"]["average"])
        self.login("other")
        self.assertEqual(self.client.get(self.path).json()["count"], 0)
        self.client.force_authenticate(None)
        self.assertEqual(self.client.get(self.path).json()["count"], 0)

    def test_admin_approval_publishes_and_hiding_removes_rating(self):
        self.post()
        item = ProductFeedback.objects.get()
        self.login("admin")
        route = f"/api/v1/feedback-admin/{item.pk}/"
        self.assertEqual(self.client.patch(route, {"status": "APPROVED"}).status_code, 200)
        self.client.force_authenticate(None)
        response = self.client.get(self.path).json()
        self.assertEqual(response["summary"]["average"], 5)
        self.assertEqual(response["summary"]["count"], 1)
        self.assertEqual(response["results"][0]["author"], "Khách mua thật")
        self.assertNotIn(self.s["customer"].email, str(response))
        self.assertNotIn("verified_order", response["results"][0])
        self.login("admin")
        self.client.patch(route, {"status": "HIDDEN"})
        self.client.force_authenticate(None)
        self.assertEqual(self.client.get(self.path).json()["count"], 0)

    def test_customer_and_branch_staff_cannot_moderate(self):
        item = self.approved()
        assign(self.s["other"], self.s["a"], "manage_sales")
        for who in ["customer", "other"]:
            self.login(who)
            self.assertEqual(
                self.client.patch(
                    f"/api/v1/feedback-admin/{item.pk}/", {"status": "HIDDEN"}
                ).status_code,
                403,
            )
            self.assertEqual(self.client.get("/api/v1/feedback-admin/").status_code, 403)

    def test_rating_validation_and_inactive_product(self):
        for rating in [0, 6, "bad"]:
            self.assertEqual(self.post(rating=rating).status_code, 400)
        self.s["p"].is_active = False
        self.s["p"].save()
        self.assertEqual(self.client.get(self.path).status_code, 404)
        self.assertEqual(self.post().status_code, 404)

    def test_question_does_not_require_purchase_or_allow_rating(self):
        self.login("other")
        for i in range(2):
            self.assertEqual(
                self.client.post(
                    self.path, {"kind": "QUESTION", "body": f"Câu hỏi số {i} về sản phẩm"}
                ).status_code,
                201,
            )
        self.assertEqual(
            self.client.post(
                self.path, {"kind": "QUESTION", "rating": 5, "body": "Câu hỏi có sao không?"}
            ).status_code,
            400,
        )
        self.assertFalse(ProductFeedback.objects.filter(verified_order__isnull=False).exists())

    def test_customer_reply_is_pending_and_cannot_claim_staff_badge(self):
        item = self.approved("QUESTION")
        self.login("other")
        response = self.client.post(
            f"/api/v1/feedback/{item.pk}/replies/",
            {"body": "Tôi cũng cần tư vấn", "is_staff_reply": True, "status": "APPROVED"},
        )
        self.assertEqual(response.status_code, 201)
        self.assertFalse(response.json()["is_staff_reply"])
        self.assertEqual(response.json()["status"], "PENDING")
        self.client.force_authenticate(None)
        self.assertEqual(
            self.client.get(self.path + "?kind=QUESTION").json()["results"][0]["replies"], []
        )
        self.login("admin")
        queue = self.client.get("/api/v1/feedback-admin/?status=PENDING").json()
        self.assertEqual(queue["results"][0]["id"], item.pk)
        reply = FeedbackReply.objects.get()
        self.client.patch(f"/api/v1/feedback-admin/replies/{reply.pk}/", {"status": "APPROVED"})
        self.client.force_authenticate(None)
        self.assertEqual(
            len(self.client.get(self.path + "?kind=QUESTION").json()["results"][0]["replies"]), 1
        )

    def test_only_admin_can_answer_review_and_staff_answer_is_explicit(self):
        item = self.approved()
        self.login("customer")
        self.assertEqual(
            self.client.post(
                f"/api/v1/feedback/{item.pk}/replies/", {"body": "Tự trả lời"}
            ).status_code,
            403,
        )
        self.login("admin")
        response = self.client.post(
            f"/api/v1/feedback/{item.pk}/replies/", {"body": "Cảm ơn bạn đã đánh giá."}
        )
        self.assertEqual(response.status_code, 201)
        self.assertTrue(response.json()["is_staff_reply"])
        self.assertEqual(response.json()["author"], "TechRetail")

    def test_photos_sanitized_and_pending_urls_not_accessible_to_other_users(self):
        self.login()
        response = self.client.post(
            self.path,
            {"kind": "REVIEW", "rating": 5, "body": "Ảnh sản phẩm thực tế", "photos": [photo()]},
            format="multipart",
        )
        self.assertEqual(response.status_code, 201, response.content)
        url = response.json()["photos"][0]
        own = self.client.get(url)
        self.assertEqual(own.status_code, 200)
        self.assertNotIn(b"private metadata", own.content)
        self.assertEqual(own["Content-Type"], "image/jpeg")
        self.login("other")
        self.assertEqual(self.client.get(url).status_code, 404)
        self.login("admin")
        self.client.patch(
            f"/api/v1/feedback-admin/{response.json()['id']}/", {"status": "APPROVED"}
        )
        self.client.force_authenticate(None)
        self.assertEqual(self.client.get(url).status_code, 200)

    def test_bad_or_too_many_photos_are_rejected_without_orphan_rows(self):
        self.login()
        for files in [
            [SimpleUploadedFile("fake.jpg", b"<script>bad</script>", content_type="image/jpeg")],
            [photo() for _ in range(6)],
        ]:
            response = self.client.post(
                self.path,
                {"kind": "REVIEW", "rating": 5, "body": "Ảnh không hợp lệ", "photos": files},
                format="multipart",
            )
            self.assertEqual(response.status_code, 400, response.content)
        self.assertFalse(ProductFeedback.objects.exists())
        self.assertFalse(FeedbackPhoto.objects.exists())

    def test_helpful_votes_are_idempotent_and_reports_are_private(self):
        item = self.approved()
        self.login("other")
        for _ in range(2):
            self.assertEqual(
                self.client.put(
                    f"/api/v1/feedback/{item.pk}/helpful/", {"helpful": True}, format="json"
                ).status_code,
                200,
            )
            self.assertEqual(
                self.client.post(
                    f"/api/v1/feedback/{item.pk}/report/", {"reason": "Nội dung cần kiểm tra"}
                ).status_code,
                200,
            )
        self.assertEqual(FeedbackVote.objects.count(), 1)
        self.assertEqual(FeedbackReport.objects.count(), 1)
        self.assertNotIn("reports", self.client.get(self.path).json()["results"][0])
        self.client.put(f"/api/v1/feedback/{item.pk}/helpful/", {"helpful": False}, format="json")
        self.assertFalse(FeedbackVote.objects.exists())
        self.login("admin")
        self.assertEqual(
            self.client.get("/api/v1/feedback-admin/?reported=true&status=").json()["count"], 1
        )

    def test_search_filters_and_pagination(self):
        for i in range(22):
            ProductFeedback.objects.create(
                product=self.s["p"],
                author=self.s["other"],
                kind="QUESTION",
                body=f"Câu hỏi {i}",
                status="APPROVED",
            )
        first = self.client.get(self.path + "?kind=QUESTION").json()
        self.assertEqual(first["count"], 22)
        self.assertEqual(len(first["results"]), 20)
        self.assertEqual(
            len(self.client.get(self.path + "?kind=QUESTION&page=2").json()["results"]), 2
        )
        self.assertEqual(
            self.client.get(self.path + "?kind=QUESTION&search=khôngcó").json()["count"], 0
        )

    def test_csrf_required_on_submission(self):
        browser = APIClient(enforce_csrf_checks=True)
        browser.force_login(self.s["customer"])
        response = browser.post(self.path, {"kind": "QUESTION", "body": "Câu hỏi bảo mật"})
        self.assertEqual(response.status_code, 403)
        self.assertFalse(ProductFeedback.objects.exists())

    def test_throttle_limits_repeated_submissions(self):
        self.login()
        responses = [
            self.client.post(
                self.path, {"kind": "QUESTION", "body": "Hỏi về cấu hình máy"}
            ).status_code
            for _ in range(11)
        ]
        self.assertEqual(responses.count(201), 10)
        self.assertEqual(responses[-1], 429)

    def test_real_sessions_multipart_csrf_and_admin_moderation_in_one_cookie_jar(self):
        browser = APIClient(enforce_csrf_checks=True)

        def call(path, method="get", data=None, staff=False, multipart=False):
            host = "localhost:5174" if staff else "localhost:5173"
            extra = {"HTTP_HOST": host, "HTTP_ORIGIN": "http://" + host}
            if method != "get":
                token = browser.get("/api/v1/auth/csrf/", **extra).json()["csrfToken"]
                extra["HTTP_X_CSRFTOKEN"] = token
            return getattr(browser, method)(
                path, data or {}, format="multipart" if multipart else "json", **extra
            )

        for who, staff in [("customer", False), ("admin", True)]:
            login = call(
                "/api/v1/auth/login/",
                "post",
                {"email": self.s[who].email, "password": "Test-password-2026!"},
                staff=staff,
            )
            self.assertEqual(login.status_code, 200, login.content)
        self.assertTrue(call(self.path).json()["viewer"]["can_review"])
        created = call(
            self.path,
            "post",
            {
                "kind": "REVIEW",
                "rating": 4,
                "body": "Đánh giá qua phiên và ảnh thực.",
                "photos": [photo()],
            },
            multipart=True,
        )
        self.assertEqual(created.status_code, 201, created.content)
        route = f"/api/v1/feedback-admin/{created.json()['id']}/"
        self.assertEqual(call(route, "patch", {"status": "APPROVED"}).status_code, 403)
        self.assertEqual(call(route, "patch", {"status": "APPROVED"}, staff=True).status_code, 200)
        public = call(self.path).json()
        self.assertEqual(public["summary"]["average"], 4)
        self.assertTrue(public["results"][0]["is_mine"])
        self.assertEqual(call(created.json()["photos"][0]).status_code, 200)
        self.assertEqual(call("/api/v1/auth/me/").json()["user"]["id"], self.s["customer"].pk)
