from datetime import timedelta
from decimal import Decimal
from django.test import TestCase
from django.contrib.auth.models import AnonymousUser
from django.utils import timezone
from django.db import IntegrityError, transaction
from django.core.management import call_command
from rest_framework.exceptions import PermissionDenied
from common.errors import BusinessError
from apps.inventory.models import (
    InventoryBalance,
    StockDocument,
    StockDocumentItem,
    StockTransfer,
    StockTransferItem,
    StockMovement,
    InventoryReservation,
)
from apps.inventory.services import post_document, transition_transfer
from apps.orders.models import Order, Invoice
from apps.orders.services import create_order, transition_order, finish_pos, expire_orders
from apps.payments.services import record_payment
from .factories import scenario, checkout, assign


class BusinessTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.s = scenario()

    def order(self, **extra):
        return create_order(
            checkout(self.s, **extra), self.s["customer"], "test", str(Order.objects.count())
        )

    def ship(self, order):
        for a in ["confirm", "pack", "ship"]:
            transition_order(order.pk, a, self.s["admin"])

    def test_checkout_reserves_and_snapshots(self):
        o = self.order()
        self.s["balance"].refresh_from_db()
        self.assertEqual((self.s["balance"].on_hand, self.s["balance"].reserved), (10, 1))
        self.assertEqual(o.grand_total, Decimal("1234000"))
        self.assertEqual(o.items.get().sku, "TEST-SKU")

    def test_checkout_idempotent_and_payload_mismatch(self):
        d = checkout(self.s)
        o = create_order(d, self.s["customer"], "same", "key")
        self.assertEqual(o.pk, create_order(d, self.s["customer"], "same", "key").pk)
        with self.assertRaises(BusinessError):
            create_order({**d, "recipient_name": "Changed"}, self.s["customer"], "same", "key")
        self.assertEqual(Order.objects.count(), 1)

    def test_insufficient_rolls_back_all(self):
        with self.assertRaises(BusinessError):
            self.order(items=[{"variant": self.s["v"].pk, "quantity": 11}])
        self.assertFalse(Order.objects.exists())
        self.assertFalse(InventoryReservation.objects.exists())

    def test_guest_does_not_create_account(self):
        from apps.accounts.models import User

        n = User.objects.count()
        o = create_order(checkout(self.s), AnonymousUser(), "guest", "key")
        self.assertIsNone(o.customer.user)
        self.assertEqual(User.objects.count(), n)

    def test_customer_cancel_pending_releases_once(self):
        o = self.order()
        transition_order(o.pk, "cancel", self.s["customer"], "Đổi ý")
        transition_order(o.pk, "cancel", self.s["admin"], "Đổi ý")
        self.s["balance"].refresh_from_db()
        self.assertEqual((self.s["balance"].on_hand, self.s["balance"].reserved), (10, 0))

    def test_confirmed_does_not_expire(self):
        o = self.order()
        transition_order(o.pk, "confirm", self.s["admin"])
        Order.objects.filter(pk=o.pk).update(expires_at=timezone.now() - timedelta(hours=1))
        self.assertEqual(expire_orders(), 0)

    def test_expiration_releases_once(self):
        o = self.order()
        Order.objects.filter(pk=o.pk).update(expires_at=timezone.now() - timedelta(seconds=1))
        self.assertEqual(expire_orders(), 1)
        self.assertEqual(expire_orders(), 0)
        self.s["balance"].refresh_from_db()
        self.assertEqual(self.s["balance"].reserved, 0)

    def test_checkout_releases_expired_pending_in_same_warehouse(self):
        old = self.order(items=[{"variant": self.s["v"].pk, "quantity": 10}])
        Order.objects.filter(pk=old.pk).update(expires_at=timezone.now() - timedelta(seconds=1))
        new = self.order()
        old.refresh_from_db()
        self.assertEqual(old.status, "CANCELLED")
        self.assertEqual(new.status, "PENDING")
        self.s["balance"].refresh_from_db()
        self.assertEqual(self.s["balance"].reserved, 1)

    def test_expired_confirm_persists_cancel(self):
        o = self.order()
        Order.objects.filter(pk=o.pk).update(expires_at=timezone.now() - timedelta(seconds=1))
        with self.assertRaises(BusinessError):
            transition_order(o.pk, "confirm", self.s["admin"])
        o.refresh_from_db()
        self.assertEqual(o.status, "CANCELLED")

    def test_ship_once_and_no_cancel_after_shipping(self):
        o = self.order()
        self.ship(o)
        transition_order(o.pk, "ship", self.s["admin"])
        self.s["balance"].refresh_from_db()
        self.assertEqual((self.s["balance"].on_hand, self.s["balance"].reserved), (9, 0))
        self.assertEqual(StockMovement.objects.filter(kind="SALE").count(), 1)
        with self.assertRaises(BusinessError):
            transition_order(o.pk, "cancel", self.s["admin"], "Test")

    def test_complete_requires_payment_and_invoice_once(self):
        o = self.order()
        self.ship(o)
        with self.assertRaises(BusinessError):
            transition_order(o.pk, "complete", self.s["admin"])
        record_payment(o.pk, self.s["admin"], "CAPTURE", "payment")
        transition_order(o.pk, "complete", self.s["admin"])
        transition_order(o.pk, "complete", self.s["admin"])
        self.assertEqual(Invoice.objects.count(), 1)
        self.assertEqual(StockMovement.objects.filter(kind="SALE").count(), 1)

    def test_payment_deduplicates_and_mismatch(self):
        o = self.order()
        p = record_payment(o.pk, self.s["admin"], "CAPTURE", "key", "ref")
        self.assertEqual(p.pk, record_payment(o.pk, self.s["admin"], "CAPTURE", "key", "ref").pk)
        with self.assertRaises(BusinessError):
            record_payment(o.pk, self.s["admin"], "CAPTURE", "key", "changed")

    def test_bank_reference_required(self):
        o = self.order(payment_method="BANK_TRANSFER")
        with self.assertRaises(BusinessError):
            record_payment(o.pk, self.s["admin"], "CAPTURE", "key")

    def test_cancellation_creates_refund_obligation(self):
        o = self.order()
        record_payment(o.pk, self.s["admin"], "CAPTURE", "capture")
        transition_order(o.pk, "cancel", self.s["customer"], "Đổi ý")
        o.refresh_from_db()
        self.assertEqual(o.payment_status, "REFUND_PENDING")
        record_payment(o.pk, self.s["admin"], "REFUND", "refund", "Manual-ref-1")
        o.refresh_from_db()
        self.assertEqual(o.payment_status, "REFUNDED")

    def test_customer_cannot_record_payment(self):
        with self.assertRaises(PermissionDenied):
            record_payment(self.order().pk, self.s["customer"], "CAPTURE", "key")

    def test_expired_payment_does_not_capture(self):
        o = self.order()
        Order.objects.filter(pk=o.pk).update(expires_at=timezone.now() - timedelta(seconds=1))
        with self.assertRaises(BusinessError):
            record_payment(o.pk, self.s["admin"], "CAPTURE", "key")
        self.assertEqual(o.transactions.count(), 0)
        o.refresh_from_db()
        self.assertEqual(o.status, "CANCELLED")

    def test_pos_draft_no_reservation_finish_atomic(self):
        o = create_order(
            checkout(self.s, channel="IN_STORE", payment_method="CASH", fulfillment="PICKUP"),
            self.s["admin"],
            "pos",
            "key",
        )
        self.assertFalse(o.reservations.exists())
        finish_pos(o.pk, self.s["admin"], "cash")
        finish_pos(o.pk, self.s["admin"], "cash")
        self.s["balance"].refresh_from_db()
        self.assertEqual(self.s["balance"].on_hand, 9)
        self.assertEqual(o.transactions.count(), 1)
        self.assertEqual(Invoice.objects.count(), 1)

    def test_pos_bank_failure_rolls_back_stock(self):
        o = create_order(
            checkout(
                self.s, channel="IN_STORE", payment_method="BANK_TRANSFER", fulfillment="PICKUP"
            ),
            self.s["admin"],
            "pos",
            "key",
        )
        with self.assertRaises(BusinessError):
            finish_pos(o.pk, self.s["admin"], "cash")
        self.s["balance"].refresh_from_db()
        self.assertEqual(self.s["balance"].on_hand, 10)

    def test_branch_scope_mutations(self):
        assign(self.s["other"], self.s["b"], "manage_sales", "manage_payments")
        with self.assertRaises(PermissionDenied):
            transition_order(self.order().pk, "confirm", self.s["other"])

    def doc(self, kind="IN", quantity=2):
        d = StockDocument.objects.create(
            warehouse=self.s["wa"], kind=kind, reason="Test", created_by=self.s["admin"]
        )
        StockDocumentItem.objects.create(document=d, variant=self.s["v"], quantity=quantity)
        return d

    def test_document_post_once(self):
        d = self.doc()
        post_document(d.pk, self.s["admin"])
        post_document(d.pk, self.s["admin"])
        self.s["balance"].refresh_from_db()
        self.assertEqual(self.s["balance"].on_hand, 12)

    def test_manual_out_does_not_use_reserved(self):
        self.order(items=[{"variant": self.s["v"].pk, "quantity": 10}])
        d = self.doc("OUT", 1)
        with self.assertRaises(BusinessError):
            post_document(d.pk, self.s["admin"])
        d.refresh_from_db()
        self.assertEqual(d.status, "DRAFT")

    def test_negative_adjustment_protected(self):
        with self.assertRaises(BusinessError):
            post_document(self.doc("ADJUST", -11).pk, self.s["admin"])

    def test_document_cancellation_immutable(self):
        d = self.doc()
        post_document(d.pk, self.s["admin"], True)
        with self.assertRaises(BusinessError):
            post_document(d.pk, self.s["admin"])

    def transfer(self):
        t = StockTransfer.objects.create(
            source=self.s["wa"], destination=self.s["wb"], reason="Test", created_by=self.s["admin"]
        )
        StockTransferItem.objects.create(transfer=t, variant=self.s["v"], quantity=2)
        return t

    def test_transfer_lifecycle_and_receive_once(self):
        t = self.transfer()
        transition_transfer(t.pk, "approve", self.s["admin"])
        self.s["balance"].refresh_from_db()
        self.assertEqual(self.s["balance"].reserved, 2)
        transition_transfer(t.pk, "dispatch", self.s["admin"])
        self.s["balance"].refresh_from_db()
        self.assertEqual((self.s["balance"].on_hand, self.s["balance"].reserved), (8, 0))
        self.assertFalse(InventoryBalance.objects.filter(warehouse=self.s["wb"]).exists())
        transition_transfer(t.pk, "receive", self.s["admin"])
        transition_transfer(t.pk, "receive", self.s["admin"])
        self.assertEqual(InventoryBalance.objects.get(warehouse=self.s["wb"]).on_hand, 2)

    def test_transfer_cancel_approved_releases(self):
        t = self.transfer()
        transition_transfer(t.pk, "approve", self.s["admin"])
        transition_transfer(t.pk, "cancel", self.s["admin"])
        self.s["balance"].refresh_from_db()
        self.assertEqual((self.s["balance"].on_hand, self.s["balance"].reserved), (10, 0))

    def test_transfer_cannot_cancel_in_transit(self):
        t = self.transfer()
        for a in ["approve", "dispatch"]:
            transition_transfer(t.pk, a, self.s["admin"])
        with self.assertRaises(BusinessError):
            transition_transfer(t.pk, "cancel", self.s["admin"])

    def test_destination_staff_cannot_dispatch(self):
        assign(self.s["other"], self.s["b"], "manage_stock")
        t = self.transfer()
        transition_transfer(t.pk, "approve", self.s["admin"])
        with self.assertRaises(PermissionDenied):
            transition_transfer(t.pk, "dispatch", self.s["other"])
        transition_transfer(t.pk, "dispatch", self.s["admin"])
        transition_transfer(t.pk, "receive", self.s["other"])

    def test_balance_constraint(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            InventoryBalance.objects.filter(pk=self.s["balance"].pk).update(reserved=11)

    def test_reservation_xor_constraint(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            InventoryReservation.objects.create(balance=self.s["balance"], quantity=1)

    def test_reconciliation_after_lifecycle(self):
        o = self.order()
        self.ship(o)
        call_command("reconcile_inventory", verbosity=0)
