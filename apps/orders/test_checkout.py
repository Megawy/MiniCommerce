import threading
import time
from decimal import Decimal

import pytest
from django.db import connection
from django.urls import reverse
from rest_framework.test import APIClient

from apps.cart.models import Cart, CartItem
from apps.payments import services as payment_services
from apps.payments.models import Payment
from apps.products.models import Category, Product

from . import services
from .models import Order, OrderItem

CHECKOUT = reverse("order-checkout")


@pytest.fixture
def category(db):
    return Category.objects.create(name="Keyboards", slug="keyboards")


@pytest.fixture
def keyboard(category):
    return Product.objects.create(
        category=category, name="Mechanical Keyboard", slug="mech", price=Decimal("99.99"), stock=5
    )


@pytest.fixture
def mouse(category):
    return Product.objects.create(
        category=category, name="Mouse", slug="mouse", price=Decimal("10.00"), stock=10
    )


def fill_cart(user, *lines):
    cart, _ = Cart.objects.get_or_create(user=user)
    for product, quantity in lines:
        CartItem.objects.create(cart=cart, product=product, quantity=quantity)
    return cart


def decline(amount):
    raise payment_services.PaymentFailed("Payment declined.")


def assert_nothing_happened(user, product, stock, cart_quantity):
    product.refresh_from_db()
    assert product.stock == stock
    assert not Order.objects.exists()
    assert not OrderItem.objects.exists()
    assert not Payment.objects.exists()
    assert CartItem.objects.get(cart__user=user, product=product).quantity == cart_quantity


# --- Success --------------------------------------------------------------

@pytest.mark.django_db
def test_successful_checkout(customer_client, user, keyboard, mouse):
    fill_cart(user, (keyboard, 2), (mouse, 3))

    res = customer_client.post(CHECKOUT)

    assert res.status_code == 201
    assert res.data["status"] == "PAID"
    assert res.data["total"] == "229.98"  # 2*99.99 + 3*10.00
    assert [(i["product"]["name"], i["quantity"], i["price"], i["subtotal"]) for i in res.data["items"]] == [
        ("Mechanical Keyboard", 2, "99.99", "199.98"),
        ("Mouse", 3, "10.00", "30.00"),
    ]

    order = Order.objects.get()
    assert order.user == user
    assert order.total == sum(i.subtotal for i in order.items.all())

    keyboard.refresh_from_db()
    mouse.refresh_from_db()
    assert (keyboard.stock, mouse.stock) == (3, 7)

    payment = order.payment
    assert payment.status == Payment.Status.SUCCESS
    assert payment.amount == Decimal("229.98")
    assert payment.transaction_id.startswith("mock_")

    assert Cart.objects.filter(user=user).exists()
    assert not CartItem.objects.filter(cart__user=user).exists()


@pytest.mark.django_db
def test_checkout_snapshots_price(customer_client, user, keyboard):
    fill_cart(user, (keyboard, 1))
    customer_client.post(CHECKOUT)

    keyboard.price = Decimal("50.00")
    keyboard.save()

    item = OrderItem.objects.get()
    assert item.price == Decimal("99.99")


@pytest.mark.django_db
def test_checkout_ignores_client_supplied_total(customer_client, user, keyboard):
    fill_cart(user, (keyboard, 1))
    res = customer_client.post(CHECKOUT, {"total": "0.01", "price": "0.01"}, format="json")
    assert res.data["total"] == "99.99"


# --- Rejections that must leave no trace ----------------------------------

@pytest.mark.django_db
def test_empty_cart_rejected(customer_client, user):
    Cart.objects.create(user=user)
    res = customer_client.post(CHECKOUT)
    assert res.status_code == 400
    assert res.data == {"detail": "Your cart is empty."}
    assert not Order.objects.exists()


@pytest.mark.django_db
def test_no_cart_rejected(customer_client):
    res = customer_client.post(CHECKOUT)
    assert res.status_code == 400
    assert not Order.objects.exists()


@pytest.mark.django_db
def test_inactive_product_rejected(customer_client, user, keyboard):
    fill_cart(user, (keyboard, 1))
    keyboard.is_active = False
    keyboard.save()

    res = customer_client.post(CHECKOUT)

    assert res.status_code == 400
    assert "no longer available" in res.data["detail"]
    assert_nothing_happened(user, keyboard, stock=5, cart_quantity=1)


@pytest.mark.django_db
def test_insufficient_stock_rolls_back(customer_client, user, keyboard, mouse):
    keyboard.stock = 2
    keyboard.save()
    # mouse is valid and comes first by pk? No: keyboard pk < mouse pk. Either way nothing may persist.
    fill_cart(user, (mouse, 1), (keyboard, 3))

    res = customer_client.post(CHECKOUT)

    assert res.status_code == 400
    assert res.data == {"detail": "Insufficient stock for Mechanical Keyboard. Available: 2, requested: 3."}
    assert_nothing_happened(user, keyboard, stock=2, cart_quantity=3)
    mouse.refresh_from_db()
    assert mouse.stock == 10


@pytest.mark.django_db
def test_payment_failure_rolls_back_everything(customer_client, user, keyboard, monkeypatch):
    fill_cart(user, (keyboard, 2))
    monkeypatch.setattr(payment_services, "charge", decline)

    res = customer_client.post(CHECKOUT)

    assert res.status_code == 400
    assert res.data == {"detail": "Payment declined."}
    # Order, items, stock deduction and the PENDING payment row were all written, then rolled back.
    assert_nothing_happened(user, keyboard, stock=5, cart_quantity=2)


@pytest.mark.django_db
def test_double_checkout(customer_client, user, keyboard):
    fill_cart(user, (keyboard, 1))
    assert customer_client.post(CHECKOUT).status_code == 201
    res = customer_client.post(CHECKOUT)
    assert res.status_code == 400
    assert Order.objects.count() == 1


# --- Access ---------------------------------------------------------------

@pytest.mark.django_db
def test_checkout_uses_only_own_cart(customer_client, user, django_user_model, keyboard):
    bob = django_user_model.objects.create_user(email="bob@example.com", password="x")
    fill_cart(bob, (keyboard, 2))
    Cart.objects.create(user=user)  # caller's cart is empty

    res = customer_client.post(CHECKOUT)

    assert res.status_code == 400
    assert not Order.objects.exists()
    assert CartItem.objects.get(cart__user=bob).quantity == 2
    keyboard.refresh_from_db()
    assert keyboard.stock == 5


@pytest.mark.django_db
def test_unauthenticated_checkout_returns_401(api_client):
    assert api_client.post(CHECKOUT).status_code == 401


# --- Concurrency ----------------------------------------------------------

@pytest.mark.django_db(transaction=True)  # real commits, so two connections can see the data
def test_concurrent_checkouts_cannot_oversell(django_user_model, category, monkeypatch):
    """Two users, one unit of stock, two simultaneous checkouts on separate DB connections.

    The payment step sleeps while holding the transaction open. Without select_for_update
    the second thread would read stock=1 during that sleep and both would succeed
    (verified by temporarily removing select_for_update: this test then fails).
    With the lock, the second thread blocks until the first commits, then sees stock=0.
    """
    product = Product.objects.create(category=category, name="Last One", slug="last", price=10, stock=1)
    users = [
        django_user_model.objects.create_user(email=f"u{i}@example.com", password="x") for i in range(2)
    ]
    for u in users:
        fill_cart(u, (product, 1))

    real_charge = payment_services.charge

    def slow_charge(amount):
        time.sleep(0.5)  # widen the race window while row locks are held
        return real_charge(amount)

    monkeypatch.setattr(payment_services, "charge", slow_charge)

    barrier = threading.Barrier(2)
    results = []

    def run(u):
        try:
            barrier.wait()
            services.checkout(u)
            results.append("ok")
        except services.CheckoutError as exc:
            results.append(str(exc))
        finally:
            connection.close()  # each thread has its own connection

    threads = [threading.Thread(target=run, args=(u,)) for u in users]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    product.refresh_from_db()
    assert sorted(results) == ["Insufficient stock for Last One. Available: 0, requested: 1.", "ok"]
    assert product.stock == 0
    assert Order.objects.count() == 1
