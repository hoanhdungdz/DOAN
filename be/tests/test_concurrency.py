import threading
from concurrent.futures import ThreadPoolExecutor
from django.test import TransactionTestCase
from django.db import connections, connection
from django.contrib.auth.models import AnonymousUser
from apps.orders.services import create_order
from apps.orders.models import Order
from apps.inventory.models import InventoryBalance
from common.errors import BusinessError
from .factories import scenario, checkout


class MySQLConcurrencyTests(TransactionTestCase):
    def test_two_buyers_last_unit(self):
        self.assertEqual(connection.vendor, "mysql")
        s = scenario(quantity=1)
        barrier = threading.Barrier(2)
        payload = checkout(s)

        def buyer(i):
            connections.close_all()
            try:
                barrier.wait(timeout=10)
                create_order(payload, AnonymousUser(), f"buyer{i}", "request")
                return "created"
            except BusinessError as e:
                return str(e.detail.code)
            finally:
                connections.close_all()

        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(buyer, [1, 2]))
        self.assertCountEqual(results, ["created", "INSUFFICIENT_STOCK"])
        self.assertEqual(Order.objects.count(), 1)
        b = InventoryBalance.objects.get(pk=s["balance"].pk)
        self.assertEqual((b.on_hand, b.reserved), (1, 1))
