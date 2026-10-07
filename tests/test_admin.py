"""Django Admin as back-office: access, registration, read-only history, no N+1."""
from decimal import Decimal

import pytest
from django.contrib import admin
from django.db import connection
from django.test.utils import CaptureQueriesContext
from django.urls import reverse

from apps.cart.models import Cart, CartItem
from apps.orders.admin import OrderAdmin, OrderItemInline
from apps.orders.models import Order, OrderItem
from apps.payments.models import Payment
from apps.products.models import Category, Product
from apps.users.models import User

pytestmark = pytest.mark.django_db

MODELS = [User, Category, Product, Cart, CartItem, Order, OrderItem, Payment]


@pytest.fixture
def superuser(django_user_model):
    return django_user_model.objects.create_superuser(email="root@example.com", password="pw-admin-123")


@pytest.fixture
def admin_client(client, superuser):
    client.force_login(superuser)
    return client


_seq = iter(range(10_000))


def make_order(user=None):
    """A complete checkout-shaped record set: category, product, cart line, order, item, payment."""
    n = next(_seq)
    user = user or User.objects.create_user(email=f"c{n}@example.com", password="x")
    cat = Category.objects.create(name=f"Cat {n}", slug=f"cat-{n}")
    product = Product.objects.create(category=cat, name=f"P{n}", slug=f"p-{n}", price=Decimal("10.00"), stock=5)
    cart, _ = Cart.objects.get_or_create(user=user)
    CartItem.objects.create(cart=cart, product=product, quantity=1)
    order = Order.objects.create(user=user, total=Decimal("20.00"), status=Order.Status.PAID)
    OrderItem.objects.create(order=order, product=product, quantity=2, price=Decimal("10.00"))
    Payment.objects.create(order=order, amount=order.total, status=Payment.Status.SUCCESS, transaction_id=f"t{n}")
    return order


def changelist(model):
    return reverse(f"admin:{model._meta.app_label}_{model._meta.model_name}_changelist")


def change(obj):
    return reverse(f"admin:{obj._meta.app_label}_{obj._meta.model_name}_change", args=[obj.pk])


# --- Access ---------------------------------------------------------------

def test_staff_can_log_in(client, django_user_model):
    django_user_model.objects.create_user(email="ops@example.com", password="pw-ops-123", is_staff=True)
    res = client.post("/admin/login/?next=/admin/", {"username": "ops@example.com", "password": "pw-ops-123"})
    assert res.status_code == 302 and res.url == "/admin/"
    assert client.get("/admin/").status_code == 200


def test_non_staff_cannot_access_admin(client, user, password):
    res = client.post("/admin/login/", {"username": user.email, "password": password})
    assert res.status_code == 200  # form re-rendered with an error, no session
    assert client.get("/admin/").status_code == 302  # redirected to login
    client.force_login(user)
    assert client.get("/admin/").status_code == 302  # even when logged in


# --- Registration / configuration -----------------------------------------

@pytest.mark.parametrize("model", MODELS, ids=lambda m: m.__name__)
def test_model_is_registered(model):
    assert admin.site.is_registered(model)


def test_order_admin_shows_items_inline():
    assert OrderItemInline in OrderAdmin.inlines


def test_stock_is_not_list_editable():
    assert "stock" not in admin.site._registry[Product].list_editable


# --- Read-only history ----------------------------------------------------

def test_historical_fields_are_readonly(rf, superuser):
    request = rf.get("/")
    request.user = superuser
    order = make_order()
    order_admin = admin.site._registry[Order]
    assert {"user", "total", "created_at"} <= set(order_admin.get_readonly_fields(request, order))
    inline = OrderItemInline(Order, admin.site)
    assert {"price", "product", "quantity"} <= set(inline.get_readonly_fields(request, order))
    for model in (Order, OrderItem, Payment):
        assert not admin.site._registry[model].has_add_permission(request)
        assert not admin.site._registry[model].has_delete_permission(request, None)
    for model in (OrderItem, Payment):
        assert not admin.site._registry[model].has_change_permission(request, None)


def test_saving_an_order_cannot_change_total_but_can_change_status(admin_client):
    order = make_order()
    res = admin_client.post(change(order), {
        "status": "COMPLETED", "total": "0.01", "user": "999",
        "items-TOTAL_FORMS": "1", "items-INITIAL_FORMS": "1",
        "items-MIN_NUM_FORMS": "0", "items-MAX_NUM_FORMS": "1000",
        "items-0-id": str(order.items.get().pk), "items-0-order": str(order.pk), "items-0-price": "0.01",
    })
    assert res.status_code == 302, res.content[:500]
    order.refresh_from_db()
    assert order.status == "COMPLETED"
    assert order.total == Decimal("20.00")
    assert order.items.get().price == Decimal("10.00")


def test_payment_and_order_item_pages_are_view_only(admin_client):
    order = make_order()
    for obj in (order.payment, order.items.get()):
        html = admin_client.get(change(obj)).content.decode()
        assert 'name="_save"' not in html
    assert admin_client.get(reverse("admin:orders_order_add")).status_code == 403
    assert admin_client.get(reverse("admin:payments_payment_add")).status_code == 403


# --- Pages render ---------------------------------------------------------

@pytest.mark.parametrize("model", MODELS, ids=lambda m: m.__name__)
def test_changelist_and_change_pages_load(admin_client, model):
    make_order()
    assert admin_client.get(changelist(model)).status_code == 200
    obj = model.objects.first()
    assert admin_client.get(change(obj)).status_code == 200


def test_order_page_shows_snapshot_price_and_payment(admin_client):
    order = make_order()
    Product.objects.filter(pk=order.items.get().product_id).update(price=Decimal("99.00"))
    html = admin_client.get(change(order)).content.decode()
    assert "10.00" in html and "99.00" not in html  # the snapshot, not the current price
    assert order.payment.transaction_id in html


def test_search_and_filters(admin_client):
    jane = User.objects.create_user(email="jane@example.com", password="x")
    mine, other = make_order(jane), make_order()
    res = admin_client.get(changelist(Order), {"q": "jane"})
    assert list(res.context["cl"].result_list) == [mine]
    res = admin_client.get(changelist(Order), {"q": str(other.pk)})
    assert list(res.context["cl"].result_list) == [other]
    res = admin_client.get(changelist(Product), {"stock_level": "out"})
    assert res.status_code == 200 and res.context["cl"].result_count == 0


def test_user_page_never_shows_password_hash(admin_client, user):
    html = admin_client.get(change(user)).content.decode()
    algorithm, iterations, salt, hashed = user.password.split("$")
    assert user.password not in html
    assert salt not in html and hashed not in html
    assert 'name="password"' not in html  # no editable hash input


# --- Performance ----------------------------------------------------------

@pytest.mark.parametrize("model", MODELS, ids=lambda m: m.__name__)
def test_changelist_query_count_does_not_grow_with_rows(admin_client, model):
    make_order()
    with CaptureQueriesContext(connection) as few:
        admin_client.get(changelist(model))
    for _ in range(5):
        make_order()
    with CaptureQueriesContext(connection) as many:
        admin_client.get(changelist(model))
    assert len(many) == len(few), [q["sql"][:120] for q in many.captured_queries]


def test_order_change_page_queries_do_not_grow_with_items(admin_client):
    order = make_order()
    with CaptureQueriesContext(connection) as few:
        admin_client.get(change(order))
    for i in range(5):
        p = Product.objects.create(category=Category.objects.first(), name=f"X{i}", slug=f"x-{i}", price=1, stock=1)
        OrderItem.objects.create(order=order, product=p, quantity=1, price=1)
    with CaptureQueriesContext(connection) as many:
        admin_client.get(change(order))
    assert len(many) == len(few)
