from rest_framework.exceptions import APIException
from rest_framework.views import exception_handler as drf_handler
from django.db import IntegrityError, OperationalError
import logging
from rest_framework.response import Response


class BusinessError(APIException):
    status_code = 409
    default_code = "BUSINESS_CONFLICT"

    def __init__(self, message, code="BUSINESS_CONFLICT", status=409):
        self.status_code = status
        super().__init__(message, code)


def exception_handler(exc, context):
    if isinstance(exc, IntegrityError):
        exc = BusinessError("Dữ liệu trùng hoặc vi phạm ràng buộc.", "CONSTRAINT_CONFLICT")
    if isinstance(exc, OperationalError):
        exc = BusinessError("Giao dịch đang bận, vui lòng thử lại.", "DATABASE_BUSY", 503)
    response = drf_handler(exc, context)
    if response is None:
        request_id = getattr(context["request"], "request_id", "")
        logging.getLogger("tech_retail.api").error(
            "Unhandled API exception type=%s request_id=%s", type(exc).__name__, request_id
        )
        return Response(
            {
                "code": "INTERNAL_ERROR",
                "message": "Không thể xử lý yêu cầu. Vui lòng thử lại hoặc cung cấp mã yêu cầu để kiểm tra.",
                "fields": {},
                "request_id": request_id,
            },
            status=500,
        )
    if response is not None:
        data = response.data
        detail = data.get("detail") if isinstance(data, dict) else None
        response.data = {
            "code": getattr(
                detail,
                "code",
                "VALIDATION_ERROR" if response.status_code == 400 else "REQUEST_ERROR",
            ),
            "message": str(detail) if detail else "Vui lòng kiểm tra dữ liệu.",
            "fields": {} if detail else data,
            "request_id": getattr(context["request"], "request_id", ""),
        }
    return response
