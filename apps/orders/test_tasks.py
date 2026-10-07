"""Phase 13: Celery configuration, the confirmation task, and post-commit enqueueing."""
import logging
from decimal import Decimal
from unittest import mock

import pytest
from django.conf import settings
from django.urls import reverse
from kombu.exceptions import OperationalError

from apps.cart.models import Cart, CartItem
from apps.payments import services as payment_services
from apps.products.models import Category, Product
from config import celery_app

from .models import Order, OrderItem
from .tasks import send_order_confirmation

pytestmark = pytest.mark.django_db
CHECKOUT = reverse("order-checkout")
TASK = "apps.orders.tasks.send_order_confirmation"


@pytest.fixture
def product():
    cat = Category.objects.create(name="Keyboards", slug="keyboards")
    return Product.objects.create(category=cat, name="Keyboard", slug="kb", price=Decimal("50.00"), stock=5)


@pytest.fixture
def cart(user, product):
    cart = Cart.objects.create(user=user)
    CartItem.objects.create(cart=cart, product=product, quantity=2)
    return cart


def paid_order(user, product, status=Order.Status.PAID):
    order = Order.objects.create(user=user, total=Decimal("100.00"), status=status)
    OrderItem.objects.create(order=order, product=product, quantity=2, price=Decimal("50.00"))
    return order


# --- A. Configuration -----------------------------------------------------

def test_celery_app_is_configured_from_django_settings():
    celery_app.loader.import_default_modules()  # what the worker does at startup (autodiscovery)
    assert celery_app.main == "minicommerce"
    assert TASK in celery_app.tasks
    assert celery_app.conf.task_always_eager is True  # test settings: no broker, no worker
    assert celery_app.conf.task_acks_late is True
    assert celery_app.conf.broker_url == settings.CELERY_BROKER_URL
    assert not celery_app.conf.get("deprecated_settings")


# --- B/C/F. The task itself -----------------------------------------------

def test_task_sends_confirmation_once(user, product, caplog):
    order = paid_order(user, product)
    with caplog.at_level(logging.INFO, logger="apps.orders.tasks"):
        result = send_order_confirmation.delay(order.pk).get()  # eager: runs through Celery's machinery
    assert result == "sent"
    order.refresh_from_db()
    assert order.confirmation_sent_at is not None
    message = caplog.text
    assert f"order_id={order.pk}" in message and "total=100.00" in message and "items=1" in message
    assert user.email not in message and "j***@example.com" in message  # masked, no PII in logs


def test_task_is_idempotent(user, product, caplog):
    order = paid_order(user, product)
    with caplog.at_level(logging.INFO, logger="apps.orders.tasks"):
        results = [send_order_confirmation.delay(order.pk).get() for _ in range(3)]
    assert results == ["sent", "already_sent", "already_sent"]
    assert caplog.text.count("order_confirmation sent") == 1
    first = Order.objects.get(pk=order.pk).confirmation_sent_at
    send_order_confirmation.delay(order.pk)
    assert Order.objects.get(pk=order.pk).confirmation_sent_at == first  # not overwritten


def test_task_handles_missing_order(caplog):
    with caplog.at_level(logging.WARNING, logger="apps.orders.tasks"):
        assert send_order_confirmation.delay(999_999).get() == "missing"
    assert "order_id=999999 not found" in caplog.text


@pytest.mark.parametrize("status", [Order.Status.PENDING, Order.Status.CANCELLED])
def test_task_skips_unpaid_orders(user, product, status):
    order = paid_order(user, product, status=status)
    assert send_order_confirmation.delay(order.pk).get() == "not_paid"
    order.refresh_from_db()
    assert order.confirmation_sent_at is None


# --- D/E. Enqueued only after a successful commit --------------------------

def test_checkout_enqueues_task_only_after_commit(customer_client, cart, django_capture_on_commit_callbacks):
    with mock.patch.object(send_order_confirmation, "delay") as delay:
        with django_capture_on_commit_callbacks(execute=False) as callbacks:
            res = customer_client.post(CHECKOUT)
            assert res.status_code == 201
            delay.assert_not_called()  # transaction not committed yet -> nothing queued
        assert len(callbacks) == 1

        for callback in callbacks:  # simulate COMMIT
            callback()
    delay.assert_called_once_with(res.data["id"])  # payload: just the id


def test_failed_checkout_enqueues_nothing(customer_client, cart, product, django_capture_on_commit_callbacks):
    product.stock = 1  # cart wants 2
    product.save()
    with mock.patch.object(send_order_confirmation, "delay") as delay:
        with django_capture_on_commit_callbacks(execute=True) as callbacks:
            res = customer_client.post(CHECKOUT)
    assert res.status_code == 400
    assert callbacks == []  # registered callbacks of a rolled-back transaction are discarded
    delay.assert_not_called()


def test_payment_failure_enqueues_nothing(customer_client, cart, monkeypatch, django_capture_on_commit_callbacks):
    def decline(amount):
        raise payment_services.PaymentFailed("Payment declined.")

    monkeypatch.setattr(payment_services, "charge", decline)
    with mock.patch.object(send_order_confirmation, "delay") as delay:
        with django_capture_on_commit_callbacks(execute=True) as callbacks:
            assert customer_client.post(CHECKOUT).status_code == 400
    assert callbacks == []
    delay.assert_not_called()
    assert not Order.objects.exists()


def test_checkout_end_to_end_through_celery(customer_client, cart, django_capture_on_commit_callbacks):
    with django_capture_on_commit_callbacks(execute=True):
        res = customer_client.post(CHECKOUT)  # commit -> on_commit -> delay() -> task (eager)
    assert res.status_code == 201
    order = Order.objects.get(pk=res.data["id"])
    assert order.status == Order.Status.PAID
    assert order.confirmation_sent_at is not None


def test_broker_outage_does_not_fail_committed_checkout(customer_client, cart, django_capture_on_commit_callbacks):
    with mock.patch.object(send_order_confirmation, "delay", side_effect=OperationalError("broker down")):
        with django_capture_on_commit_callbacks(execute=True):
            res = customer_client.post(CHECKOUT)
    assert res.status_code == 201  # robust=True: logged, the order stays committed
    assert Order.objects.get(pk=res.data["id"]).confirmation_sent_at is None
