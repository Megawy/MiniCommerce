from decimal import Decimal
from io import StringIO

import pytest
from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.core.management.base import CommandError

from apps.cart.models import CartItem
from apps.orders.models import Order, OrderItem
from apps.payments.models import Payment
from apps.products.models import Category, Product
from apps.users.management.commands import seed_demo

pytestmark = pytest.mark.django_db
User = get_user_model()
PASSWORD = "test-demo-pass"


@pytest.fixture(autouse=True)
def debug_on(settings):
    settings.DEBUG = True  # the test runner forces DEBUG=False; the command is dev-only


@pytest.fixture(autouse=True)
def no_ambient_demo_password(monkeypatch):
    # Tests must not depend on the caller's environment (e.g. Docker Compose loads
    # DEMO_PASSWORD from .env into the container). Each test sets it explicitly if needed.
    monkeypatch.delenv("DEMO_PASSWORD", raising=False)


def seed(*args):
    out = StringIO()
    call_command("seed_demo", "--password", PASSWORD, *args, stdout=out)
    return out.getvalue()


def counts():
    return {
        "users": User.objects.count(), "categories": Category.objects.count(),
        "products": Product.objects.count(), "cart_items": CartItem.objects.count(),
        "orders": Order.objects.count(), "order_items": OrderItem.objects.count(),
        "payments": Payment.objects.count(),
    }


EXPECTED = {"users": 3, "categories": 4, "products": 8, "cart_items": 2,
            "orders": 2, "order_items": 3, "payments": 2}


def test_first_run_creates_demo_data():
    output = seed()
    assert counts() == EXPECTED
    assert "Demo data ready." in output
    assert PASSWORD not in output


def test_second_and_third_runs_create_no_duplicates():
    seed()
    seed()
    seed()
    assert counts() == EXPECTED


def test_default_run_does_not_overwrite_changes():
    seed()
    Product.objects.filter(slug="wireless-mouse").update(stock=3)
    seed()
    assert Product.objects.get(slug="wireless-mouse").stock == 3


def test_reset_restores_demo_records_and_keeps_other_data(django_user_model):
    seed()
    # unrelated, non-demo data (including an order for a demo user)
    outsider = django_user_model.objects.create_user(email="real@customer.com", password="x")
    other_cat = Category.objects.create(name="Cables", slug="cables")
    other_product = Product.objects.create(category=other_cat, name="HDMI", slug="hdmi", price=5, stock=9)
    jane = User.objects.get(email="jane@example.com")
    real_order = Order.objects.create(user=jane, total=5)
    OrderItem.objects.create(order=real_order, product=other_product, quantity=1, price=5)
    # tamper with demo data
    Product.objects.filter(slug="mechanical-keyboard").update(price=Decimal("1.00"), stock=0)
    old_demo_order_ids = set(Order.objects.filter(payment__isnull=False).values_list("id", flat=True))

    seed("--reset")

    kb = Product.objects.get(slug="mechanical-keyboard")
    assert (kb.price, kb.stock) == (Decimal("99.99"), 25)
    new_demo = Order.objects.filter(payment__transaction_id__startswith="demo_txn_")
    assert new_demo.count() == 2
    assert not old_demo_order_ids & set(new_demo.values_list("id", flat=True))  # recreated
    # untouched
    assert User.objects.filter(pk=outsider.pk).exists()
    assert Product.objects.filter(pk=other_product.pk).exists()
    assert Order.objects.filter(pk=real_order.pk).exists()
    assert Order.objects.count() == 3


def test_failure_rolls_back_everything(monkeypatch):
    def boom(self, order, txn):
        raise RuntimeError("payment step failed")

    monkeypatch.setattr(seed_demo.Command, "create_payment", boom)  # last step
    with pytest.raises(RuntimeError):
        seed()
    assert all(v == 0 for v in counts().values())


def test_refuses_default_password_when_debug_off(settings):
    settings.DEBUG = False
    with pytest.raises(CommandError):
        call_command("seed_demo", stdout=StringIO())
    assert User.objects.count() == 0


def test_accepts_configured_demo_password_when_debug_off(settings, monkeypatch):
    settings.DEBUG = False
    monkeypatch.setenv("DEMO_PASSWORD", PASSWORD)  # explicit opt-in, as in Docker's .env
    call_command("seed_demo", stdout=StringIO())
    assert User.objects.get(email="admin@example.com").check_password(PASSWORD)


def test_data_integrity():
    seed()
    admin = User.objects.get(email="admin@example.com")
    assert admin.is_staff and admin.is_superuser
    for user in User.objects.all():
        assert user.password.startswith("pbkdf2_sha256$")
        assert user.check_password(PASSWORD)

    for product in Product.objects.select_related("category"):
        assert product.category.slug in {"keyboards", "mice", "monitors", "headsets"}
        assert product.price >= 0 and product.stock >= 0

    for item in CartItem.objects.select_related("product"):
        assert 0 < item.quantity <= item.product.stock
        assert item.product.is_active

    for order in Order.objects.prefetch_related("items"):
        items = list(order.items.all())
        assert items
        assert order.total == sum(i.price * i.quantity for i in items)
        assert order.status in {Order.Status.PAID, Order.Status.COMPLETED}
        assert order.payment.status == Payment.Status.SUCCESS
        assert order.payment.amount == order.total
