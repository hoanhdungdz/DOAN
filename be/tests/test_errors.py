from types import SimpleNamespace
from django.test import SimpleTestCase
from common.errors import exception_handler


class ErrorContractTests(SimpleTestCase):
    def test_unexpected_exception_does_not_expose_message_or_stack(self):
        response = exception_handler(
            ValueError("SENSITIVE_TEST_TOKEN"),
            {"request": SimpleNamespace(request_id="test-request")},
        )
        self.assertEqual(response.status_code, 500)
        self.assertEqual(response.data["code"], "INTERNAL_ERROR")
        self.assertNotIn("SENSITIVE_TEST_TOKEN", str(response.data))
        self.assertEqual(response.data["request_id"], "test-request")
