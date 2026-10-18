import uuid
from decimal import Decimal, InvalidOperation
from django.http import JsonResponse


class RequestContextMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request.request_id = str(uuid.uuid4())
        if request.path.startswith("/api/"):
            for key in (
                "category",
                "brand",
                "store",
                "warehouse",
                "balance",
                "customer",
                "spec_definition",
            ):
                value = request.GET.get(key)
                if value and (
                    not value.isascii() or not value.isdecimal() or not 0 < int(value) < 2**63
                ):
                    return JsonResponse(
                        {
                            "code": "INVALID_FILTER",
                            "message": "Bộ lọc ID không hợp lệ.",
                            "fields": {key: "Cần số nguyên dương."},
                            "request_id": request.request_id,
                        },
                        status=400,
                    )
            for key in ("spec_min", "spec_max"):
                value = request.GET.get(key)
                if value:
                    try:
                        valid = Decimal(value).is_finite()
                    except InvalidOperation:
                        valid = False
                    if not valid:
                        return JsonResponse(
                            {
                                "code": "INVALID_FILTER",
                                "message": "Bộ lọc số không hợp lệ.",
                                "fields": {key: "Cần số hữu hạn."},
                                "request_id": request.request_id,
                            },
                            status=400,
                        )
        response = self.get_response(request)
        response["X-Request-ID"] = request.request_id
        return response
