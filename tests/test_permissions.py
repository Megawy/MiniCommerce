"""Who may do what: one table per role, plus cross-user ownership.

401 = not authenticated, 403 = authenticated but not allowed, 404 = not in *your* queryset.
"""
from decimal import Decimal

import pytest
from django.urls import reverse
from rest_framework.test import APIClient

from apps.cart.models import Cart, CartItem
from apps.cart.serializers import AddCartItemSerializer
from apps.orders.models import Order, OrderItem
from apps.products.models import Category, Product

pytestmark = pytest.mark.django_db


@pytest.fixture
def product():
    cat = Category.objects.create(name="Keyboards", slug="keyboards")
    return Product.objects.create(category=cat, name="Keyboard", slug="kb", price=Decimal("10"), stock=5)


@pytest.fixture
def bob(django_user_model):
    return django_user_model.objects.create_user(email="bob@example.com", password="x")


@pytest.fixture
def bob_item(bob, product):
    cart = Cart.objects.create(user=bob)
    return CartItem.objects.create(cart=cart, product=product, quantity=2)


@pytest.fixture
def bob_order(bob, product):
    order = Order.objects.create(user=bob, total=Decimal("10"), status=Order.Status.PAID)
    OrderItem.objects.create(order=order, product=product, quantity=1, price=Decimal("10"))
    return order


def new_product_payload(product):
    return {"name": "New", "slug": "new", "price": "1.00", "stock": 1, "category_id": product.category_id}


def call(client, method, url, data=None):
    return getattr(client, method)(url, data or {}, format="json")


PRODUCTS = "/api/products/"
CATEGORIES = "/api/categories/"


# --- Role matrix ----------------------------------------------------------

@pytest.mark.parametrize("method,url,expected", [
    ("get", PRODUCTS, 200),
    ("get", CATEGORIES, 200),
    ("get", "/api/health/", 200),
    ("post", PRODUCTS, 401),
    ("post", CATEGORIES, 401),
    ("get", "/api/cart/", 401),
    ("post", "/api/cart/items/", 401),
    ("get", "/api/orders/", 401),
    ("post", "/api/orders/checkout/", 401),
    ("get", "/api/auth/me/", 401),
])
def test_anonymous(api_client, product, method, url, expected):
    assert call(api_client, method, url).status_code == expected


@pytest.mark.parametrize("method,url,expected", [
    ("get", PRODUCTS, 200),
    ("get", CATEGORIES, 200),
    ("post", PRODUCTS, 403),           # authenticated, but not staff
    ("post", CATEGORIES, 403),
    ("get", "/api/cart/", 200),
    ("get", "/api/orders/", 200),
    ("post", "/api/orders/checkout/", 400),  # allowed; rejected by business rule (empty cart)
    ("get", "/api/auth/me/", 200),
])
def test_customer(customer_client, product, method, url, expected):
    assert call(customer_client, method, url).status_code == expected


@pytest.mark.parametrize("method", ["put", "patch", "delete"])
def test_customer_cannot_change_catalog(customer_client, product, method):
    assert call(customer_client, method, f"{PRODUCTS}{product.id}/").status_code == 403
    assert call(customer_client, method, f"{CATEGORIES}{product.category_id}/").status_code == 403


def test_staff_can_write_catalog(staff_client, product):
    assert call(staff_client, "post", PRODUCTS, new_product_payload(product)).status_code == 201
    assert call(staff_client, "post", CATEGORIES, {"name": "Mice", "slug": "mice"}).status_code == 201


def test_inactive_product_hidden_from_customer_visible_to_staff(customer_client, staff_client, product):
    product.is_active = False
    product.save()
    url = f"{PRODUCTS}{product.id}/"
    assert customer_client.get(url).status_code == 404
    assert staff_client.get(url).status_code == 200


# --- Authentication -------------------------------------------------------

def test_invalid_token_is_rejected(api_client):
    api_client.credentials(HTTP_AUTHORIZATION="Bearer not-a-real-token")
    assert api_client.get("/api/cart/").status_code == 401


def test_invalid_token_is_rejected_even_on_public_endpoint(api_client):
    # Authentication runs before permissions: a *bad* token is an error even where
    # anonymous access is allowed. (No token at all is fine.)
    api_client.credentials(HTTP_AUTHORIZATION="Bearer not-a-real-token")
    assert api_client.get(PRODUCTS).status_code == 401


def test_real_jwt_reaches_protected_endpoint(api_client, user, password):
    access = api_client.post("/api/auth/login/", {"email": user.email, "password": password}).data["access"]
    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")
    assert api_client.get("/api/cart/").status_code == 200


def test_login_is_throttled(api_client, user):
    codes = [
        api_client.post("/api/auth/login/", {"email": user.email, "password": "wrong"}).status_code
        for _ in range(11)
    ]
    assert codes[:10] == [401] * 10
    assert codes[10] == 429


# --- Ownership (queryset scoping -> 404) ----------------------------------

def test_cannot_modify_other_users_cart_item(customer_client, bob_item):
    url = f"/api/cart/items/{bob_item.id}/"
    assert customer_client.patch(url, {"quantity": 1}, format="json").status_code == 404
    assert customer_client.delete(url).status_code == 404
    bob_item.refresh_from_db()
    assert bob_item.quantity == 2


def test_cannot_see_other_users_cart(customer_client, bob_item):
    assert customer_client.get("/api/cart/").data["items"] == []


def test_cannot_access_other_users_order(customer_client, bob_order):
    assert customer_client.get(f"/api/orders/{bob_order.id}/").status_code == 404
    assert customer_client.get("/api/orders/").data["count"] == 0


def test_staff_api_is_also_scoped_to_own_orders(staff_client, bob_order):
    # By design: staff manage all orders in Django Admin, not through the customer API.
    assert staff_client.get(f"/api/orders/{bob_order.id}/").status_code == 404


def test_cannot_checkout_other_users_cart(customer_client, bob_item, product):
    assert customer_client.post("/api/orders/checkout/").status_code == 400
    bob_item.refresh_from_db()
    product.refresh_from_db()
    assert (bob_item.quantity, product.stock, Order.objects.count()) == (2, 5, 0)


# --- Error handling -------------------------------------------------------

def test_unique_race_returns_409_not_500(customer_client, user, product, monkeypatch):
    """Simulates the cart double-click race: validation saw no line, but one exists at save."""
    customer_client.post("/api/cart/items/", {"product_id": product.id, "quantity": 1}, format="json")
    real_validate = AddCartItemSerializer.validate

    def stale_validate(self, attrs):
        attrs = real_validate(self, attrs)
        attrs["existing"] = None  # as if the other request hadn't committed yet
        return attrs

    monkeypatch.setattr(AddCartItemSerializer, "validate", stale_validate)
    res = customer_client.post("/api/cart/items/", {"product_id": product.id, "quantity": 1}, format="json")
    assert res.status_code == 409
    assert res.data == {"detail": "Conflicting request, please retry."}
