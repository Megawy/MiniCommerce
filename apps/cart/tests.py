from decimal import Decimal

import pytest
from django.db import IntegrityError
from django.urls import reverse
from rest_framework.test import APIClient

from apps.products.models import Category, Product

from .models import Cart, CartItem

pytestmark = pytest.mark.django_db

CART = reverse("cart")
ITEMS = reverse("cart-item-list")


def item_url(pk):
    return reverse("cart-item-detail", args=[pk])


@pytest.fixture
def category():
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


@pytest.fixture
def other_client(django_user_model):
    other = django_user_model.objects.create_user(email="other@example.com", password="x")
    client = APIClient()
    client.force_authenticate(other)
    return client


def add(client, product, quantity):
    return client.post(ITEMS, {"product_id": product.id, "quantity": quantity}, format="json")


# --- Cart creation --------------------------------------------------------

def test_authenticated_user_gets_empty_cart(customer_client, user):
    res = customer_client.get(CART)
    assert res.status_code == 200
    assert res.data["items"] == []
    assert res.data["total"] == "0.00"
    assert Cart.objects.filter(user=user).exists()


def test_same_user_always_gets_same_cart(customer_client, user):
    first = customer_client.get(CART).data["id"]
    second = customer_client.get(CART).data["id"]
    assert first == second
    assert Cart.objects.filter(user=user).count() == 1


def test_different_users_have_different_carts(customer_client, other_client):
    assert customer_client.get(CART).data["id"] != other_client.get(CART).data["id"]


def test_db_allows_only_one_cart_per_user(user):
    Cart.objects.create(user=user)
    with pytest.raises(IntegrityError):
        Cart.objects.create(user=user)


# --- Add item -------------------------------------------------------------

def test_add_item(customer_client, keyboard):
    res = add(customer_client, keyboard, 2)
    assert res.status_code == 201
    assert res.data["quantity"] == 2
    assert res.data["subtotal"] == "199.98"


def test_add_inactive_product_rejected(customer_client, keyboard):
    keyboard.is_active = False
    keyboard.save()
    res = add(customer_client, keyboard, 1)
    assert res.status_code == 400
    assert "product_id" in res.data


def test_add_nonexistent_product_returns_404(customer_client):
    res = customer_client.post(ITEMS, {"product_id": 999999, "quantity": 1}, format="json")
    assert res.status_code == 404


@pytest.mark.parametrize("quantity", [0, -3])
def test_add_non_positive_quantity_rejected(customer_client, keyboard, quantity):
    res = add(customer_client, keyboard, quantity)
    assert res.status_code == 400
    assert "quantity" in res.data


def test_add_above_stock_rejected(customer_client, keyboard):
    res = add(customer_client, keyboard, 6)  # stock = 5
    assert res.status_code == 400
    assert "quantity" in res.data


def test_adding_existing_product_increases_quantity(customer_client, keyboard):
    add(customer_client, keyboard, 2)
    res = add(customer_client, keyboard, 3)
    assert res.status_code == 200
    assert res.data["quantity"] == 5
    assert CartItem.objects.count() == 1


def test_combined_quantity_cannot_exceed_stock(customer_client, keyboard):
    add(customer_client, keyboard, 3)
    res = add(customer_client, keyboard, 3)  # 6 > 5
    assert res.status_code == 400
    assert CartItem.objects.get().quantity == 3


def test_db_rejects_duplicate_product_in_cart(user, keyboard):
    cart = Cart.objects.create(user=user)
    CartItem.objects.create(cart=cart, product=keyboard, quantity=1)
    with pytest.raises(IntegrityError):
        CartItem.objects.create(cart=cart, product=keyboard, quantity=1)


# --- Update ---------------------------------------------------------------

@pytest.fixture
def item(customer_client, keyboard):
    return CartItem.objects.get(pk=add(customer_client, keyboard, 1).data["id"])


def test_update_quantity(customer_client, item):
    res = customer_client.patch(item_url(item.id), {"quantity": 4}, format="json")
    assert res.status_code == 200
    item.refresh_from_db()
    assert item.quantity == 4


def test_update_invalid_quantity_rejected(customer_client, item):
    res = customer_client.patch(item_url(item.id), {"quantity": 0}, format="json")
    assert res.status_code == 400


def test_update_above_stock_rejected(customer_client, item):
    res = customer_client.patch(item_url(item.id), {"quantity": 6}, format="json")
    assert res.status_code == 400


def test_update_cannot_change_product(customer_client, item, mouse, keyboard):
    customer_client.patch(item_url(item.id), {"quantity": 2, "product_id": mouse.id}, format="json")
    item.refresh_from_db()
    assert item.product_id == keyboard.id


def test_user_cannot_update_other_users_item(other_client, item):
    res = other_client.patch(item_url(item.id), {"quantity": 2}, format="json")
    assert res.status_code == 404  # not 403: don't reveal that the id exists
    item.refresh_from_db()
    assert item.quantity == 1


# --- Remove / clear -------------------------------------------------------

def test_remove_item(customer_client, item):
    res = customer_client.delete(item_url(item.id))
    assert res.status_code == 204
    assert not CartItem.objects.exists()


def test_user_cannot_remove_other_users_item(other_client, item):
    res = other_client.delete(item_url(item.id))
    assert res.status_code == 404
    assert CartItem.objects.filter(pk=item.id).exists()


def test_clear_cart_keeps_cart(customer_client, user, keyboard, mouse):
    add(customer_client, keyboard, 1)
    add(customer_client, mouse, 2)
    res = customer_client.delete(CART)
    assert res.status_code == 204
    assert Cart.objects.filter(user=user).exists()
    assert not CartItem.objects.filter(cart__user=user).exists()


# --- API access -----------------------------------------------------------

@pytest.mark.parametrize("method,url", [
    ("get", CART), ("delete", CART), ("post", ITEMS),
    ("patch", "/api/cart/items/1/"), ("delete", "/api/cart/items/1/"),
])
def test_unauthenticated_requests_rejected(api_client, method, url):
    assert getattr(api_client, method)(url).status_code == 401


def test_user_only_sees_own_cart(customer_client, other_client, keyboard, mouse):
    add(customer_client, keyboard, 1)
    add(other_client, mouse, 3)
    res = customer_client.get(CART)
    assert [i["product"]["name"] for i in res.data["items"]] == ["Mechanical Keyboard"]


def test_cart_total(customer_client, keyboard, mouse):
    add(customer_client, keyboard, 2)  # 199.98
    add(customer_client, mouse, 3)     # 30.00
    assert customer_client.get(CART).data["total"] == "229.98"


# --- Query performance ----------------------------------------------------

def test_cart_query_count_is_constant(customer_client, user, category, django_assert_num_queries):
    cart = Cart.objects.create(user=user)
    for i in range(10):
        p = Product.objects.create(category=category, name=f"P{i}", slug=f"p{i}", price=1, stock=9)
        CartItem.objects.create(cart=cart, product=p, quantity=1)
    # 1: SELECT cart   2: SELECT items JOIN product.  Without optimisation: 2 + 10.
    with django_assert_num_queries(2):
        res = customer_client.get(CART)
    assert len(res.data["items"]) == 10
