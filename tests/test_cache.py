"""Phase 12: Redis-backed Django cache, shared throttling, and the category-list cache."""
import os
import subprocess
import sys
from unittest import mock

import pytest
from django.conf import settings as django_settings
from django.core.cache import cache
from rest_framework.throttling import ScopedRateThrottle

from apps.products.cache import CATEGORY_LIST_KEY, CATEGORY_LIST_TTL
from apps.products.models import Category

pytestmark = pytest.mark.django_db

CATEGORIES = "/api/categories/"
needs_redis = pytest.mark.skipif(not os.environ.get("REDIS_URL"), reason="REDIS_URL not set (no Redis)")


def read_in_another_process(key, **env):
    """Read a cache key from a *separate Python process* — like another Gunicorn worker."""
    code = ("import django; django.setup(); from django.core.cache import cache; "
            f"v = cache.get({key!r}); print('MISSING' if v is None else v)")
    result = subprocess.run(
        [sys.executable, "-c", code], capture_output=True, text=True, check=True, timeout=60,
        env={**os.environ, "DJANGO_SETTINGS_MODULE": "config.settings.test", **env},
    )
    return result.stdout.strip()


@pytest.fixture
def categories():
    return [Category.objects.create(name=n, slug=n.lower()) for n in ("Keyboards", "Mice", "Monitors")]


# --- Backend --------------------------------------------------------------

def test_cache_backend_follows_configuration():
    backend = django_settings.CACHES["default"]
    if os.environ.get("REDIS_URL"):
        assert backend["BACKEND"] == "django_redis.cache.RedisCache"
        assert backend["LOCATION"].endswith("/2")  # tests use DB 2, the app uses DB 1
        assert backend["OPTIONS"]["IGNORE_EXCEPTIONS"] is True
    else:
        assert backend["BACKEND"] == "django.core.cache.backends.locmem.LocMemCache"


def test_cache_api_roundtrip():
    cache.set("phase12:probe", {"ok": True}, 30)
    assert cache.get("phase12:probe") == {"ok": True}
    cache.delete("phase12:probe")
    assert cache.get("phase12:probe") is None


@needs_redis
def test_redis_cache_is_shared_between_processes_locmem_is_not():
    cache.set("phase12:shared", "from-worker-1", 30)
    assert read_in_another_process("phase12:shared") == "from-worker-1"
    # The lesson of this phase: an in-memory cache is private to each process.
    assert read_in_another_process("phase12:shared", REDIS_URL="") == "MISSING"


# --- Throttling -----------------------------------------------------------

def login(api_client):
    return api_client.post("/api/auth/login/", {"email": "nobody@example.com", "password": "wrong"})


def test_throttle_history_lives_in_django_cache(api_client):
    key = ScopedRateThrottle.cache_format % {"scope": "auth", "ident": "127.0.0.1"}
    for _ in range(3):
        login(api_client)
    assert len(cache.get(key)) == 3  # DRF stores request timestamps under this key


@needs_redis
def test_throttle_state_is_shared_across_workers(api_client):
    key = ScopedRateThrottle.cache_format % {"scope": "auth", "ident": "127.0.0.1"}
    codes = [login(api_client).status_code for _ in range(10)]
    assert codes == [401] * 10
    # Another process (= another Gunicorn worker) sees the same 10 attempts...
    assert read_in_another_process(key).count(",") == 9
    # ...so the 11th attempt is refused no matter which worker handles it.
    assert login(api_client).status_code == 429


# --- Category list cache --------------------------------------------------

def test_first_read_populates_cache_second_read_skips_database(api_client, categories, django_assert_num_queries):
    assert cache.get(CATEGORY_LIST_KEY) is None
    first = api_client.get(CATEGORIES)
    assert [c["slug"] for c in cache.get(CATEGORY_LIST_KEY)] == ["keyboards", "mice", "monitors"]
    with django_assert_num_queries(0):  # served entirely from the cache
        second = api_client.get(CATEGORIES)
    assert second.json() == first.json()


def test_cache_key_and_ttl(api_client, categories):
    assert CATEGORY_LIST_KEY == "catalog:categories:v1"
    with mock.patch.object(cache, "set", wraps=cache.set) as spy:
        api_client.get(CATEGORIES)
    spy.assert_called_once()
    key, _data, timeout = spy.call_args.args
    assert (key, timeout) == (CATEGORY_LIST_KEY, CATEGORY_LIST_TTL) == ("catalog:categories:v1", 60)


def test_response_shape_unchanged(api_client, categories):
    body = api_client.get(CATEGORIES).json()
    assert set(body) == {"count", "next", "previous", "results"}
    assert body["count"] == 3
    assert set(body["results"][0]) == {"id", "name", "slug", "created_at", "updated_at"}


def test_query_parameters_do_not_collide(api_client, categories):
    page1 = api_client.get(CATEGORIES, {"page_size": 1}).json()
    page2 = api_client.get(CATEGORIES, {"page_size": 1, "page": 2}).json()
    full = api_client.get(CATEGORIES).json()
    assert [c["slug"] for c in page1["results"]] == ["keyboards"]
    assert [c["slug"] for c in page2["results"]] == ["mice"]
    assert [c["slug"] for c in full["results"]] == ["keyboards", "mice", "monitors"]
    # Absolute pagination links are built per request, never cached with another host.
    other_host = api_client.get(CATEGORIES, {"page_size": 1}, HTTP_HOST="127.0.0.1").json()
    assert other_host["next"].startswith("http://127.0.0.1/")
    assert page1["next"].startswith("http://testserver/")


def test_api_write_invalidates_cache(staff_client, categories, django_capture_on_commit_callbacks):
    staff_client.get(CATEGORIES)
    assert cache.get(CATEGORY_LIST_KEY) is not None
    with django_capture_on_commit_callbacks(execute=True):
        res = staff_client.post(CATEGORIES, {"name": "Headsets", "slug": "headsets"}, format="json")
    assert res.status_code == 201
    assert cache.get(CATEGORY_LIST_KEY) is None
    assert "headsets" in [c["slug"] for c in staff_client.get(CATEGORIES).json()["results"]]


@pytest.mark.parametrize("change", ["update", "delete"])
def test_orm_and_admin_writes_invalidate_cache(api_client, categories, change, django_capture_on_commit_callbacks):
    api_client.get(CATEGORIES)
    with django_capture_on_commit_callbacks(execute=True):
        if change == "update":
            categories[0].name = "Keyboards & Keypads"
            categories[0].save()
        else:
            categories[2].delete()
    assert cache.get(CATEGORY_LIST_KEY) is None
    fresh = [c["name"] for c in api_client.get(CATEGORIES).json()["results"]]
    assert fresh == (["Keyboards & Keypads", "Mice", "Monitors"] if change == "update" else ["Keyboards", "Mice"])


def test_invalidation_waits_for_commit(api_client, categories, django_capture_on_commit_callbacks):
    api_client.get(CATEGORIES)
    with django_capture_on_commit_callbacks(execute=False) as callbacks:
        Category.objects.create(name="Cables", slug="cables")
        assert cache.get(CATEGORY_LIST_KEY) is not None  # not yet: transaction still open
    assert len(callbacks) == 1


# --- Redis unavailable ----------------------------------------------------

@pytest.fixture
def redis_down(settings):
    """Point the cache at a Redis that isn't there (connection refused)."""
    settings.CACHES = {"default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": "redis://127.0.0.1:1/1",
        "OPTIONS": {"SOCKET_CONNECT_TIMEOUT": 1, "SOCKET_TIMEOUT": 1, "IGNORE_EXCEPTIONS": True},
    }}


def test_redis_outage_falls_back_to_postgresql(redis_down, api_client, staff_client, categories,
                                               django_capture_on_commit_callbacks):
    assert cache.get("anything") is None  # errors are swallowed -> behaves as a miss
    res = api_client.get(CATEGORIES)
    assert res.status_code == 200 and res.json()["count"] == 3  # served from PostgreSQL
    with django_capture_on_commit_callbacks(execute=True):
        created = staff_client.post(CATEGORIES, {"name": "Cables", "slug": "cables"}, format="json")
    assert created.status_code == 201  # writes still succeed; failed invalidation is harmless
    assert Category.objects.filter(slug="cables").exists()


def test_redis_outage_does_not_break_login(redis_down, api_client, user, password):
    res = api_client.post("/api/auth/login/", {"email": user.email, "password": password})
    assert res.status_code == 200  # throttling fails open while the cache is unavailable
