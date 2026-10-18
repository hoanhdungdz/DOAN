from drf_spectacular.authentication import SessionScheme
from rest_framework import serializers


class CsrfSessionScheme(SessionScheme):
    target_class = "common.authentication.CsrfSessionAuthentication"
    priority = 1


class ErrorSerializer(serializers.Serializer):
    code = serializers.CharField()
    message = serializers.CharField()
    fields = serializers.JSONField()
    request_id = serializers.CharField()


class MessageSerializer(serializers.Serializer):
    message = serializers.CharField(required=False)
    delivery_mode = serializers.CharField(required=False)


class AuthInputSerializer(serializers.Serializer):
    email = serializers.EmailField(required=False)
    password = serializers.CharField(required=False, write_only=True)
    full_name = serializers.CharField(required=False)
    token = serializers.CharField(required=False, write_only=True)
    current_password = serializers.CharField(required=False, write_only=True)


class UserInfoSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    email = serializers.EmailField()
    full_name = serializers.CharField()
    is_admin = serializers.BooleanField()
    permissions = serializers.ListField(child=serializers.CharField())
    stores = serializers.ListField(child=serializers.IntegerField())


class SessionResponseSerializer(MessageSerializer):
    user = UserInfoSerializer(allow_null=True, required=False)
    csrfToken = serializers.CharField(required=False)


class FeatureSerializer(serializers.Serializer):
    google_login = serializers.BooleanField()
    facebook_login = serializers.BooleanField()
    gemini = serializers.BooleanField()
    ai_status = serializers.CharField()


class LookupResponseSerializer(MessageSerializer):
    challenge = serializers.UUIDField(required=False)
    expires_in = serializers.IntegerField(required=False)
    code = serializers.CharField(required=False)
    status = serializers.CharField(required=False)
    payment_status = serializers.CharField(required=False)
    grand_total = serializers.DecimalField(max_digits=18, decimal_places=2, required=False)
    items = serializers.ListField(child=serializers.DictField(), required=False)


def errors_hook(result, generator, request, public):
    schema = {
        "type": "object",
        "required": ["code", "message"],
        "properties": {
            "code": {"type": "string"},
            "message": {"type": "string"},
            "fields": {"type": "object", "additionalProperties": True},
            "request_id": {"type": "string", "format": "uuid"},
        },
    }
    result["components"]["schemas"]["BusinessError"] = schema
    for path in result["paths"].values():
        for method, operation in path.items():
            if method not in ("get", "post", "put", "patch", "delete"):
                continue
            for code in ["400", "403", "404", "409", "429", "503"]:
                operation.setdefault("responses", {}).setdefault(
                    code,
                    {
                        "description": "Structured validation, permission, business or availability error.",
                        "content": {
                            "application/json": {
                                "schema": {"$ref": "#/components/schemas/BusinessError"}
                            }
                        },
                    },
                )
    return result
