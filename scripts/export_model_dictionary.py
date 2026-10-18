"""Generate the database field dictionary from the migrated Django models."""

import os
import sys
from pathlib import Path

base = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(base / "be"))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
import django

django.setup()
from django.apps import apps
from django.db import connection

labels = {
    "auth",
    "contenttypes",
    "sessions",
    "accounts",
    "products",
    "stores",
    "inventory",
    "customers",
    "orders",
    "payments",
    "suppliers",
    "common",
}
lines = [
    "# Từ điển trường dữ liệu\n",
    "Sinh từ Django models; kiểu DB trên MySQL thực đang chạy. PK bigint tự tăng, FK tham chiếu theo cột target, mọi constraint do migration quản lý.\n",
]
for model in apps.get_models(include_auto_created=True):
    if model._meta.app_label not in labels:
        continue
    lines += [
        f"## {model._meta.label} — `{model._meta.db_table}`\n",
        "| Field | MySQL type | Null | Key / reference |",
        "|---|---|---|---|",
    ]
    for field in model._meta.fields:
        ref = (
            "PK"
            if field.primary_key
            else (
                "FK " + field.related_model._meta.label
                if field.is_relation
                else "UNIQUE"
                if field.unique
                else ""
            )
        )
        lines.append(f"| {field.name} | {field.db_type(connection)} | {field.null} | {ref} |")
    lines += [
        "\nConstraints: "
        + ("; ".join(str(c) for c in model._meta.constraints) or "Django PK/FK/field unique."),
        "\nIndexes: "
        + ("; ".join(str(i) for i in model._meta.indexes) or "PK/unique/FK indexes mặc định."),
        "",
    ]
(base / "be" / "MODEL_DICTIONARY.md").write_text("\n".join(lines), encoding="utf-8")
print("be/MODEL_DICTIONARY.md generated from real model definitions.")
