"""CORS: the Angular dev server may call the API; other origins may not."""
import pytest

pytestmark = pytest.mark.django_db
ANGULAR = "http://localhost:4200"


def preflight(client, origin, path="/api/auth/login/"):
    return client.options(
        path,
        HTTP_ORIGIN=origin,
        HTTP_ACCESS_CONTROL_REQUEST_METHOD="POST",
        HTTP_ACCESS_CONTROL_REQUEST_HEADERS="authorization,content-type",
    )


def test_preflight_from_angular_dev_server_is_allowed(client):
    res = preflight(client, ANGULAR)
    assert res.status_code == 200
    assert res["Access-Control-Allow-Origin"] == ANGULAR
    assert "authorization" in res["Access-Control-Allow-Headers"]
    assert "POST" in res["Access-Control-Allow-Methods"]
    assert "Access-Control-Allow-Credentials" not in res  # JWT in header, not cookies


def test_simple_request_from_angular_gets_cors_header(client):
    res = client.get("/api/health/", HTTP_ORIGIN=ANGULAR)
    assert res["Access-Control-Allow-Origin"] == ANGULAR


@pytest.mark.parametrize("origin", ["https://evil.example", "http://localhost:3000"])
def test_other_origins_are_not_allowed(client, origin):
    res = preflight(client, origin)
    assert "Access-Control-Allow-Origin" not in res


def test_no_wildcard(settings):
    assert settings.CORS_ALLOWED_ORIGINS == ["http://localhost:4200", "http://127.0.0.1:4200"]
    assert not getattr(settings, "CORS_ALLOW_ALL_ORIGINS", False)
