from decimal import Decimal

import pytest
from django.db import IntegrityError
from django.urls import reverse
from rest_framework.test import APIClient

from apps.products.models import Category, Product

from .models import Order, OrderItem

pytestmark = pytest.mark.django_db

ORDERS = reverse("order-list")


def order_url(pk):
    return reverse("order-detail", args=[pk])


@pytest.fixture
def keyboard():
    cat = Category.objects.create(name="Keyboards", slug="keyboards")
    return Product.objects.create(
        category=cat, name="Mechanical Keyboard", slug="mech", price=Decimal("100.00"), stock=10
    )


@pytest.fixture
def other_user(django_user_model):
    return django_user_model.objects.create_user(email="bob@example.com", password="x")


@pytest.fixture
def other_client(other_user):
    client = APIClient()
    client.force_authenticate(other_user)
    return client


def make_order(user, product, quantity=2, price=None):
    """Stand-in for checkout (Phase 6): snapshot the price, store the total."""
    price = product.price if price is None else price
    order = Order.objects.create(user=user, total=price * quantity)
    OrderItem.objects.create(order=order, product=product, quantity=quantity, price=price)
    return order


# --- Ownership ------------------------------------------------------------

def test_user_lists_own_orders(customer_client, user, keyboard):
    order = make_order(user, keyboard)
    res = customer_client.get(ORDERS)
    assert res.status_code == 200
    assert [o["id"] for o in res.data["results"]] == [order.id]
    assert res.data["results"][0] == {
        "id": order.id, "status": "PENDING", "total": "200.00",
        "created_at": res.data["results"][0]["created_at"],
        "updated_at": res.data["results"][0]["updated_at"],
    }


def test_user_cannot_see_other_users_orders(customer_client, other_user, keyboard):
    make_order(other_user, keyboard)
    res = customer_client.get(ORDERS)
    assert res.data["count"] == 0


def test_user_cannot_retrieve_other_users_order(customer_client, other_user, keyboard):
    order = make_order(other_user, keyboard)
    res = customer_client.get(order_url(order.id))
    assert res.status_code == 404


def test_list_is_newest_first(customer_client, user, keyboard):
    first = make_order(user, keyboard)
    second = make_order(user, keyboard)
    ids = [o["id"] for o in customer_client.get(ORDERS).data["results"]]
    assert ids == [second.id, first.id]


# --- Detail ---------------------------------------------------------------

def test_detail_returns_items_with_snapshot_price_and_subtotal(customer_client, user, keyboard):
    order = make_order(user, keyboard, quantity=2)
    res = customer_client.get(order_url(order.id))
    assert res.status_code == 200
    item = res.data["items"][0]
    assert item["product"] == {"id": keyboard.id, "name": "Mechanical Keyboard", "slug": "mech"}
    assert item["quantity"] == 2
    assert item["price"] == "100.00"
    assert item["subtotal"] == "200.00"


def test_list_does_not_include_items(customer_client, user, keyboard):
    make_order(user, keyboard)
    assert "items" not in customer_client.get(ORDERS).data["results"][0]


# --- Historical price -----------------------------------------------------

def test_price_change_does_not_affect_existing_order(customer_client, user, keyboard):
    order = make_order(user, keyboard, quantity=1)  # bought at 100

    keyboard.price = Decimal("80.00")
    keyboard.save()

    item = order.items.get()
    assert item.price == Decimal("100.00")
    res = customer_client.get(order_url(order.id))
    assert res.data["items"][0]["price"] == "100.00"
    assert res.data["total"] == "100.00"


def test_ordered_product_cannot_be_deleted(staff_client, user, keyboard):
    make_order(user, keyboard)
    res = staff_client.delete(reverse("product-detail", args=[keyboard.id]))
    assert res.status_code == 409
    assert Product.objects.filter(pk=keyboard.pk).exists()


# --- Constraints ----------------------------------------------------------

@pytest.mark.parametrize("field,value", [("quantity", 0), ("price", Decimal("-1"))])
def test_db_rejects_invalid_order_item(user, keyboard, field, value):
    order = Order.objects.create(user=user)
    data = {"order": order, "product": keyboard, "quantity": 1, "price": Decimal("1"), field: value}
    with pytest.raises(IntegrityError):
        OrderItem.objects.create(**data)


def test_db_rejects_negative_total(user):
    with pytest.raises(IntegrityError):
        Order.objects.create(user=user, total=Decimal("-1"))


# --- Permissions ----------------------------------------------------------

def test_unauthenticated_list_returns_401(api_client):
    assert api_client.get(ORDERS).status_code == 401


def test_unauthenticated_detail_returns_401(api_client, user, keyboard):
    order = make_order(user, keyboard)
    assert api_client.get(order_url(order.id)).status_code == 401


@pytest.mark.parametrize("method", ["post", "put", "patch", "delete"])
def test_write_methods_not_allowed(customer_client, user, keyboard, method):
    order = make_order(user, keyboard)
    url = ORDERS if method == "post" else order_url(order.id)
    assert getattr(customer_client, method)(url, {}, format="json").status_code == 405


# --- Pagination / queries -------------------------------------------------

def test_order_list_is_paginated(customer_client, user, keyboard):
    for _ in range(21):
        make_order(user, keyboard)
    res = customer_client.get(ORDERS)
    assert res.data["count"] == 21
    assert len(res.data["results"]) == 20
    assert res.data["next"] is not None


def test_order_detail_query_count(customer_client, user, keyboard, django_assert_num_queries):
    order = Order.objects.create(user=user, total=0)
    for i in range(10):
        p = Product.objects.create(category=keyboard.category, name=f"P{i}", slug=f"p{i}", price=1, stock=1)
        OrderItem.objects.create(order=order, product=p, quantity=1, price=1)
    # 1: SELECT order   2: SELECT items JOIN product.  Without optimisation: 2 + 10.
    with django_assert_num_queries(2):
        res = customer_client.get(order_url(order.id))
    assert len(res.data["items"]) == 10
