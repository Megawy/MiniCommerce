import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse

pytestmark = pytest.mark.django_db
User = get_user_model()

REGISTER = reverse("register")
LOGIN = reverse("login")
REFRESH = reverse("token-refresh")
ME = reverse("me")


def register_payload(**overrides):
    data = {
        "email": "user@example.com",
        "password": "StrongPassword123",
        "first_name": "John",
        "last_name": "Doe",
    }
    data.update(overrides)
    return data


def login(api_client, email, password):
    return api_client.post(LOGIN, {"email": email, "password": password}, format="json")


# --- Registration ---------------------------------------------------------

def test_register_creates_user(api_client):
    res = api_client.post(REGISTER, register_payload(), format="json")

    assert res.status_code == 201
    assert res.data["email"] == "user@example.com"
    assert User.objects.filter(email="user@example.com").exists()


def test_register_never_returns_password(api_client):
    res = api_client.post(REGISTER, register_payload(), format="json")

    assert "password" not in res.data


def test_register_hashes_password(api_client):
    api_client.post(REGISTER, register_payload(), format="json")
    user = User.objects.get(email="user@example.com")

    assert user.password != "StrongPassword123"
    assert user.password.startswith("pbkdf2_sha256$")
    assert user.check_password("StrongPassword123")


def test_register_duplicate_email_fails(api_client, user):
    res = api_client.post(REGISTER, register_payload(email=user.email.upper()), format="json")

    assert res.status_code == 400
    assert "email" in res.data


def test_register_missing_email_fails(api_client):
    payload = register_payload()
    del payload["email"]
    res = api_client.post(REGISTER, payload, format="json")

    assert res.status_code == 400
    assert "email" in res.data


def test_register_weak_password_fails(api_client):
    res = api_client.post(REGISTER, register_payload(password="123"), format="json")

    assert res.status_code == 400


# --- Login ----------------------------------------------------------------

def test_login_returns_tokens(api_client, user, password):
    res = login(api_client, user.email, password)

    assert res.status_code == 200
    assert {"access", "refresh"} <= res.data.keys()


def test_login_wrong_password_fails(api_client, user):
    res = login(api_client, user.email, "wrong-password")

    assert res.status_code == 401


def test_login_unknown_email_fails(api_client):
    res = login(api_client, "nobody@example.com", "whatever123")

    assert res.status_code == 401


# --- Me -------------------------------------------------------------------

def test_me_requires_authentication(api_client):
    res = api_client.get(ME)

    assert res.status_code == 401


def test_me_returns_current_user(api_client, user, password):
    access = login(api_client, user.email, password).data["access"]
    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")

    res = api_client.get(ME)

    assert res.status_code == 200
    assert res.data == {
        "id": user.id,
        "email": user.email,
        "first_name": "John",
        "last_name": "Doe",
    }


# --- Refresh --------------------------------------------------------------

def test_refresh_returns_new_access_token(api_client, user, password):
    refresh = login(api_client, user.email, password).data["refresh"]

    res = api_client.post(REFRESH, {"refresh": refresh}, format="json")

    assert res.status_code == 200
    assert "access" in res.data


# --- Manager --------------------------------------------------------------

def test_create_superuser_sets_flags():
    admin = User.objects.create_superuser(email="Admin@Example.COM", password="x")

    assert admin.is_staff and admin.is_superuser
    assert admin.email == "admin@example.com"
