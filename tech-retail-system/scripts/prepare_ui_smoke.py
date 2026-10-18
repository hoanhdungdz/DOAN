"""Explicit disposable test fixture; never creates demo users in application DB."""

import os
import sys
import secrets
import json
from pathlib import Path

base = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(base / "be"))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
import django

django.setup()
from django.conf import settings
from django.core.management import call_command
from apps.accounts.models import User
from apps.products.importer import import_dataset

if settings.DATABASES["default"]["NAME"] != "test_tech_retail":
    raise SystemExit(
        "Refusing: explicitly set DB_NAME=test_tech_retail before running this fixture."
    )
call_command("migrate", verbosity=0)
call_command("setup_roles")
import_dataset(settings.BASE_DIR / "data" / "final_master_dataset.json")
password = secrets.token_urlsafe(24)
user, _ = User.objects.get_or_create(
    email="ui-smoke@test.invalid",
    defaults={"is_superuser": True, "is_staff": True, "full_name": "UI smoke test (TEST ONLY)"},
)
user.set_password(password)
user.save()
runtime = base / ".runtime"
runtime.mkdir(exist_ok=True)
(runtime / "ui-smoke.json").write_text(
    json.dumps({"email": user.email, "password": password}), encoding="utf-8"
)
print(
    "Disposable UI fixture ready; credentials only in ignored .runtime/ui-smoke.json. NOT app data."
)
