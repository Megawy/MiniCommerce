from decimal import Decimal

import pytest
from django.db import IntegrityError
from django.urls import reverse

from .models import Category, Product

pytestmark = pytest.mark.django_db

CATEGORIES = reverse("category-list")
PRODUCTS = reverse("product-list")


def category_url(pk):
    return reverse("category-detail", args=[pk])


def product_url(pk):
    return reverse("product-detail", args=[pk])


@pytest.fixture
def keyboards():
    return Category.objects.create(name="Keyboards", slug="keyboards")


@pytest.fixture
def mice():
    return Category.objects.create(name="Mice", slug="mice")


def make_product(category, name, price, stock=10, is_active=True, description=""):
    from django.utils.text import slugify

    return Product.objects.create(
        category=category, name=name, slug=slugify(name), price=Decimal(price),
        stock=stock, is_active=is_active, description=description,
    )


@pytest.fixture
def catalog(keyboards, mice):
    return [
        make_product(keyboards, "Mechanical Keyboard", "99.99", description="Clicky switches"),
        make_product(keyboards, "Budget Keyboard", "19.99"),
        make_product(mice, "Gaming Mouse", "59.00", description="RGB keyboard companion"),
        make_product(mice, "Old Mouse", "5.00", is_active=False),
    ]


def names(res):
    return [p["name"] for p in res.data["results"]]


def product_payload(category, **overrides):
    data = {
        "name": "New Keyboard", "slug": "new-keyboard", "description": "",
        "price": "49.90", "stock": 5, "category_id": category.id,
    }
    data.update(overrides)
    return data


# --- Categories -----------------------------------------------------------

def test_category_list_is_public(api_client, keyboards):
    res = api_client.get(CATEGORIES)
    assert res.status_code == 200
    assert res.data["results"][0]["slug"] == "keyboards"


def test_category_detail_is_public(api_client, keyboards):
    res = api_client.get(category_url(keyboards.id))
    assert res.status_code == 200
    assert res.data["name"] == "Keyboards"


def test_category_create_requires_auth(api_client):
    res = api_client.post(CATEGORIES, {"name": "X", "slug": "x"}, format="json")
    assert res.status_code == 401


def test_category_create_forbidden_for_customer(customer_client):
    res = customer_client.post(CATEGORIES, {"name": "X", "slug": "x"}, format="json")
    assert res.status_code == 403


def test_staff_can_create_category(staff_client):
    res = staff_client.post(CATEGORIES, {"name": "Monitors", "slug": "monitors"}, format="json")
    assert res.status_code == 201
    assert Category.objects.filter(slug="monitors").exists()


def test_staff_can_update_category(staff_client, keyboards):
    res = staff_client.patch(category_url(keyboards.id), {"name": "Keebs"}, format="json")
    assert res.status_code == 200
    keyboards.refresh_from_db()
    assert keyboards.name == "Keebs"


def test_staff_can_delete_category(staff_client, keyboards):
    res = staff_client.delete(category_url(keyboards.id))
    assert res.status_code == 204
    assert not Category.objects.exists()


def test_category_with_products_cannot_be_deleted(staff_client, keyboards):
    make_product(keyboards, "K1", "10.00")
    res = staff_client.delete(category_url(keyboards.id))
    assert res.status_code == 409


# --- Products CRUD --------------------------------------------------------

def test_product_list_is_public_and_nests_category(api_client, catalog):
    res = api_client.get(PRODUCTS)
    assert res.status_code == 200
    first = res.data["results"][0]
    assert first["category"].keys() == {"id", "name", "slug"}
    assert "category_id" not in first


def test_product_list_hides_inactive_from_public(api_client, catalog):
    res = api_client.get(PRODUCTS)
    assert "Old Mouse" not in names(res)


def test_product_detail_is_public(api_client, catalog):
    res = api_client.get(product_url(catalog[0].id))
    assert res.status_code == 200
    assert res.data["price"] == "99.99"


def test_product_create_requires_staff(customer_client, keyboards):
    res = customer_client.post(PRODUCTS, product_payload(keyboards), format="json")
    assert res.status_code == 403


def test_staff_can_create_product(staff_client, keyboards):
    res = staff_client.post(PRODUCTS, product_payload(keyboards), format="json")
    assert res.status_code == 201
    assert res.data["category"]["slug"] == "keyboards"


def test_staff_can_update_product(staff_client, catalog):
    res = staff_client.patch(product_url(catalog[0].id), {"price": "89.99"}, format="json")
    assert res.status_code == 200
    catalog[0].refresh_from_db()
    assert catalog[0].price == Decimal("89.99")


def test_staff_can_delete_product(staff_client, catalog):
    res = staff_client.delete(product_url(catalog[0].id))
    assert res.status_code == 204
    assert not Product.objects.filter(id=catalog[0].id).exists()


@pytest.mark.parametrize("field,value", [("price", "-1.00"), ("stock", -1)])
def test_negative_price_or_stock_fails(staff_client, keyboards, field, value):
    res = staff_client.post(PRODUCTS, product_payload(keyboards, **{field: value}), format="json")
    assert res.status_code == 400
    assert field in res.data


def test_duplicate_slug_fails(staff_client, catalog, keyboards):
    payload = product_payload(keyboards, slug=catalog[0].slug)
    res = staff_client.post(PRODUCTS, payload, format="json")
    assert res.status_code == 400
    assert "slug" in res.data


def test_db_rejects_negative_price_even_without_validation(keyboards):
    # The CheckConstraint protects data written outside serializers too.
    with pytest.raises(IntegrityError):
        make_product(keyboards, "Broken", "-5.00")


# --- Filtering / search / ordering / pagination ---------------------------

def test_filter_by_category_slug(api_client, catalog):
    res = api_client.get(PRODUCTS, {"category": "mice"})
    assert names(res) == ["Gaming Mouse"]


def test_filter_by_is_active(staff_client, catalog):
    res = staff_client.get(PRODUCTS, {"is_active": "false"})
    assert names(res) == ["Old Mouse"]


def test_filter_min_price(api_client, catalog):
    res = api_client.get(PRODUCTS, {"min_price": 50})
    assert set(names(res)) == {"Mechanical Keyboard", "Gaming Mouse"}


def test_filter_max_price(api_client, catalog):
    res = api_client.get(PRODUCTS, {"max_price": 60})
    assert set(names(res)) == {"Budget Keyboard", "Gaming Mouse"}


def test_filter_price_range(api_client, catalog):
    res = api_client.get(PRODUCTS, {"min_price": 50, "max_price": 60})
    assert names(res) == ["Gaming Mouse"]


def test_search_matches_name_and_description(api_client, catalog):
    res = api_client.get(PRODUCTS, {"search": "keyboard"})
    # two by name, "Gaming Mouse" via its description
    assert set(names(res)) == {"Mechanical Keyboard", "Budget Keyboard", "Gaming Mouse"}


def test_ordering_by_price(api_client, catalog):
    asc = names(api_client.get(PRODUCTS, {"ordering": "price"}))
    desc = names(api_client.get(PRODUCTS, {"ordering": "-price"}))
    assert asc == ["Budget Keyboard", "Gaming Mouse", "Mechanical Keyboard"]
    assert desc == list(reversed(asc))


def test_ordering_ignores_unknown_fields(api_client, catalog):
    res = api_client.get(PRODUCTS, {"ordering": "stock"})  # not whitelisted
    assert res.status_code == 200


def test_pagination(api_client, keyboards):
    for i in range(25):
        make_product(keyboards, f"Keyboard {i}", "10.00")

    page1 = api_client.get(PRODUCTS)
    page2 = api_client.get(PRODUCTS, {"page": 2})
    small = api_client.get(PRODUCTS, {"page_size": 5})

    assert page1.data["count"] == 25
    assert len(page1.data["results"]) == 20
    assert page1.data["next"] is not None
    assert len(page2.data["results"]) == 5
    assert page2.data["next"] is None
    assert len(small.data["results"]) == 5


def test_product_list_query_count_is_constant(api_client, keyboards, django_assert_num_queries):
    for i in range(10):
        make_product(keyboards, f"Keyboard {i}", "10.00")
    # 1 COUNT for pagination + 1 SELECT ... JOIN category. Without select_related: 1 + 1 + 10.
    with django_assert_num_queries(2):
        api_client.get(PRODUCTS)
