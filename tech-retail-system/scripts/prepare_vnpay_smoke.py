"""Prepare a disposable local UI fixture, never application data or a real payment."""

import json
import os
import secrets
import sys
from pathlib import Path

base = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(base / "be"))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
import django

django.setup()
from django.conf import settings
from apps.orders.services import create_order
from tests.factories import checkout, scenario

if settings.DATABASES["default"]["NAME"] != "test_tech_retail":
    raise SystemExit(
        "Refusing: DB_NAME must be test_tech_retail. Stop test servers before running the test suite."
    )
s = scenario()
password = secrets.token_urlsafe(24)
user = s["customer"]
user.set_password(password)
user.save()
order = create_order(checkout(s, payment_method="VNPAY_SANDBOX"), user, "vnpay-ui-fixture", "order")
runtime = base / ".runtime"
runtime.mkdir(exist_ok=True)
(runtime / "vnpay-ui-fixture.json").write_text(
    json.dumps({"email": user.email, "password": password, "order": order.pk}), encoding="utf-8"
)
print("VNPay disposable fixture ready in test_tech_retail; credentials only in ignored .runtime.")
