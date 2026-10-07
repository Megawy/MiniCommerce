import pytest
from django.core.cache import cache
from rest_framework.test import APIClient


@pytest.fixture(autouse=True)
def _clear_cache():
    # Throttle counters live in the cache; don't let them leak between tests.
    cache.clear()


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def password():
    return "StrongPassword123"


@pytest.fixture
def user(django_user_model, password):
    return django_user_model.objects.create_user(
        email="john@example.com", password=password, first_name="John", last_name="Doe"
    )


@pytest.fixture
def staff_user(django_user_model, password):
    return django_user_model.objects.create_user(
        email="staff@example.com", password=password, is_staff=True
    )


@pytest.fixture
def staff_client(staff_user):
    # force_authenticate skips JWT: auth is tested in users; here we test permissions.
    client = APIClient()
    client.force_authenticate(staff_user)
    return client


@pytest.fixture
def customer_client(user):
    client = APIClient()
    client.force_authenticate(user)
    return client
