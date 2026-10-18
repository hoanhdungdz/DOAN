import csv
import io
from collections import defaultdict
from datetime import date, datetime, time, timedelta
from decimal import Decimal
from django.http import HttpResponse
from django.db.models import Sum, Count, F
from django.utils import timezone
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.exceptions import PermissionDenied
from rest_framework import serializers
from drf_spectacular.utils import extend_schema
from common.errors import BusinessError
from apps.accounts.permissions import store_ids
from apps.orders.models import Order, OrderItem
from apps.payments.models import PaymentTransaction
from apps.inventory.models import InventoryBalance, StockTransferItem


def boundaries(params):
    today = timezone.localdate()
    try:
        start = date.fromisoformat(params.get("start", today.replace(day=1).isoformat()))
        end = date.fromisoformat(params.get("end", today.isoformat()))
    except ValueError:
        raise BusinessError("Ngày lọc không hợp lệ.", "INVALID_DATE", 400)
    if end < start or (end - start).days > 3660:
        raise BusinessError("Khoảng ngày không hợp lệ.", "INVALID_DATE", 400)
    return timezone.make_aware(datetime.combine(start, time.min)), timezone.make_aware(
        datetime.combine(end + timedelta(days=1), time.min)
    )


def total(qs, field):
    return qs.aggregate(n=Sum(field))["n"] or Decimal("0")


def safe_cell(value):
    s = str(value)
    return "'" + s if s.lstrip().startswith(("=", "+", "-", "@", "\t", "\r")) else s


class ReportResponseSerializer(serializers.Serializer):
    start = serializers.DateTimeField(required=False)
    end_exclusive = serializers.DateTimeField(required=False)
    sales_gross = serializers.DecimalField(max_digits=18, decimal_places=2, required=False)
    refunds = serializers.DecimalField(max_digits=18, decimal_places=2, required=False)
    sales_net = serializers.DecimalField(max_digits=18, decimal_places=2, required=False)
    cash_captured = serializers.DecimalField(max_digits=18, decimal_places=2, required=False)
    cash_net = serializers.DecimalField(max_digits=18, decimal_places=2, required=False)
    completed_orders = serializers.IntegerField(required=False)
    customers = serializers.IntegerField(required=False)
    daily = serializers.ListField(child=serializers.DictField(), required=False)
    monthly = serializers.ListField(child=serializers.DictField(), required=False)
    order_statuses = serializers.ListField(child=serializers.DictField(), required=False)
    bestsellers = serializers.ListField(child=serializers.DictField(), required=False)
    by_store = serializers.ListField(child=serializers.DictField(), required=False)
    by_channel = serializers.ListField(child=serializers.DictField(), required=False)
    stock = serializers.DictField(required=False)


class ReportView(APIView):
    @extend_schema(
        responses=ReportResponseSerializer,
        description="kind=summary: revenue/cashflow, grouped daily/by_store/by_channel, bestsellers, stock; kind=inventory: stock; kind=export: CSV. start/end inclusive dates in Asia/Ho_Chi_Minh. See API.md.",
    )
    def get(self, request, kind):
        capability = "manage_stock" if kind == "inventory" else "view_reports"
        ids = store_ids(request.user, capability)
        if not ids:
            raise PermissionDenied()
        if request.query_params.get("store"):
            try:
                chosen = int(request.query_params["store"])
            except ValueError:
                raise BusinessError("Chi nhánh không hợp lệ.", "INVALID_FILTER", 400)
            if chosen not in ids:
                raise PermissionDenied()
            ids = [chosen]
        start, end = boundaries(request.query_params)
        orders = Order.objects.filter(warehouse__store_id__in=ids)
        completed = orders.filter(
            status="COMPLETED", paid_at__isnull=False, completed_at__gte=start, completed_at__lt=end
        )
        payments = PaymentTransaction.objects.filter(
            order__warehouse__store_id__in=ids, created_at__gte=start, created_at__lt=end
        )
        captured = total(payments.filter(kind="CAPTURE"), "amount")
        refunds = total(payments.filter(kind="REFUND"), "amount")
        balances = InventoryBalance.objects.filter(warehouse__store_id__in=ids)
        sold = OrderItem.objects.filter(order__in=completed)
        # Group in Python's configured ZoneInfo; Windows MySQL often has no named
        # timezone tables, in which case SQL CONVERT_TZ silently returns NULL.
        days = defaultdict(lambda: Decimal("0"))
        months = defaultdict(lambda: Decimal("0"))
        for instant, amount in completed.values_list("completed_at", "grand_total").iterator():
            day = timezone.localtime(instant).date()
            days[day] += amount
            months[day.strftime("%Y-%m")] += amount
        data = {
            "start": start,
            "end_exclusive": end,
            "sales_gross": str(total(completed, "grand_total")),
            "refunds": str(refunds),
            "sales_net": str(total(completed, "grand_total") - refunds),
            "cash_captured": str(captured),
            "cash_net": str(captured - refunds),
            "completed_orders": completed.count(),
            "customers": orders.filter(created_at__gte=start, created_at__lt=end)
            .values("customer_id")
            .distinct()
            .count(),
            "order_statuses": list(
                orders.filter(created_at__gte=start, created_at__lt=end)
                .values("status")
                .annotate(count=Count("id"))
            ),
            "daily": [{"day": day, "revenue": str(amount)} for day, amount in sorted(days.items())],
            "monthly": [
                {"month": month, "revenue": str(amount)} for month, amount in sorted(months.items())
            ],
            "bestsellers": list(
                sold.values("variant_id", "name", "sku")
                .annotate(quantity=Sum("quantity"), revenue=Sum("line_total"))
                .order_by("-quantity")[:10]
            ),
            "stock": {
                "on_hand": int(total(balances, "on_hand")),
                "reserved": int(total(balances, "reserved")),
                "available": int(total(balances, "on_hand") - total(balances, "reserved")),
                "low_count": balances.filter(
                    on_hand__lte=F("reserved") + F("alert_threshold")
                ).count(),
                "in_transit": int(
                    total(
                        StockTransferItem.objects.filter(
                            transfer__status="IN_TRANSIT", transfer__source__store_id__in=ids
                        ),
                        "quantity",
                    )
                ),
            },
        }
        if kind == "inventory":
            return Response(data["stock"])
        data["by_store"] = list(
            completed.values("warehouse__store_id", "warehouse__store__name")
            .annotate(revenue=Sum("grand_total"), orders=Count("id"))
            .order_by("warehouse__store_id")
        )
        data["by_channel"] = list(
            completed.values("channel")
            .annotate(revenue=Sum("grand_total"), orders=Count("id"))
            .order_by("channel")
        )
        for key in ("bestsellers", "by_store", "by_channel"):
            for row in data[key]:
                row["revenue"] = str(row["revenue"])
        if kind == "export":
            out = io.StringIO()
            w = csv.writer(out)
            w.writerow(["code", "store", "channel", "completed_at", "total"])
            for o in completed.select_related("warehouse__store").order_by("completed_at"):
                w.writerow(
                    [
                        safe_cell(x)
                        for x in [
                            o.code,
                            o.warehouse.store.name,
                            o.channel,
                            timezone.localtime(o.completed_at).isoformat(),
                            o.grand_total,
                        ]
                    ]
                )
            response = HttpResponse(
                "\ufeff" + out.getvalue(), content_type="text/csv; charset=utf-8"
            )
            response["Content-Disposition"] = 'attachment; filename="sales-report.csv"'
            return response
        if kind != "summary":
            raise BusinessError("Báo cáo không tồn tại.", "NOT_FOUND", 404)
        return Response(data)
