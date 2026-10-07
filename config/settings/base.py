"""Settings shared by every environment. dev.py / prod.py import * from here."""
from datetime import timedelta
from pathlib import Path

import environ

BASE_DIR = Path(__file__).resolve().parent.parent.parent

env = environ.Env(
    DEBUG=(bool, False),
    ALLOWED_HOSTS=(list, []),
)
# Reads .env if present; real environment variables always win.
environ.Env.read_env(BASE_DIR / ".env")

SECRET_KEY = env("SECRET_KEY")
DEBUG = env("DEBUG")
ALLOWED_HOSTS = env("ALLOWED_HOSTS")

DJANGO_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
]
THIRD_PARTY_APPS = [
    "rest_framework",
    "rest_framework_simplejwt",
    "django_filters",
    "drf_spectacular",
    "corsheaders",
]
LOCAL_APPS = [
    "common",
    "apps.users",
    "apps.products",
    "apps.cart",
    "apps.orders",
    "apps.payments",
]

AUTH_USER_MODEL = "users.User"
INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "corsheaders.middleware.CorsMiddleware",  # before CommonMiddleware (answers preflights)
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

# DATABASE_URL=postgres://user:pass@host:5432/dbname
DATABASES = {"default": env.db("DATABASE_URL")}

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ],
    # Secure by default: every endpoint needs a valid token unless it opts out with AllowAny.
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.IsAuthenticated"],
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "EXCEPTION_HANDLER": "common.exceptions.api_exception_handler",
    "DEFAULT_PAGINATION_CLASS": "common.pagination.DefaultPagination",
    # Only views that set throttle_scope are throttled (login/register).
    # Counters live in the default cache (CACHES below): shared Redis when REDIS_URL is set.
    "DEFAULT_THROTTLE_RATES": {"auth": "10/minute"},
    # JSON only for now; the browsable API is added in dev.py.
    "DEFAULT_RENDERER_CLASSES": ["rest_framework.renderers.JSONRenderer"],
}

SPECTACULAR_SETTINGS = {
    "TITLE": "MiniCommerce API",
    "DESCRIPTION": (
        "A practical Django REST API demonstrating authentication, catalog management, "
        "cart management, transactional checkout, inventory handling and API hardening.\n\n"
        "**Authentication:** `POST /api/auth/login/` returns an `access` and a `refresh` JWT. "
        "Send the access token as `Authorization: Bearer <access>` (in Swagger UI: *Authorize* "
        "→ paste the token only; the `Bearer` prefix is added for you). Access tokens expire "
        "after 15 minutes; renew them with `POST /api/auth/refresh/`.\n\n"
        "**Errors:** business and permission errors return `{\"detail\": \"...\"}`; "
        "validation errors return `{\"<field>\": [\"...\"]}`."
    ),
    "VERSION": "1.0.0",
    "SERVE_INCLUDE_SCHEMA": False,     # don't list /api/schema/ itself as an endpoint
    "COMPONENT_SPLIT_REQUEST": True,   # separate *Request schemas for write_only/read_only fields
    "SWAGGER_UI_SETTINGS": {"persistAuthorization": True},
    # Stable component names for enums that share a field name ("status").
    "ENUM_NAME_OVERRIDES": {"OrderStatusEnum": "apps.orders.models.Order.Status"},
}

# --- CORS ---------------------------------------------------------------------------
# Browsers only let a page on another origin (Angular dev server :4200) call the API if the
# API allows that exact origin. Explicit allowlist, never "allow all". Empty by default:
# in production the frontend is served from the same origin (reverse proxy), so no CORS.
# JWTs travel in the Authorization header, not cookies -> no CORS_ALLOW_CREDENTIALS.
CORS_ALLOWED_ORIGINS = env.list("CORS_ALLOWED_ORIGINS", default=[])

# --- Cache --------------------------------------------------------------------------
# Redis is a shared, disposable cache (throttle counters, short-lived catalog reads).
# PostgreSQL stays the source of truth: everything here may vanish at any time.
REDIS_URL = env("REDIS_URL", default="")  # e.g. redis://redis:6379/1 (DB 1 = Django cache)
if REDIS_URL:
    CACHES = {
        "default": {
            "BACKEND": "django_redis.cache.RedisCache",
            "LOCATION": REDIS_URL,
            "KEY_PREFIX": "minicommerce",
            "TIMEOUT": 300,  # default TTL; callers pass explicit, shorter ones
            "OPTIONS": {
                # Fail fast and degrade to "cache miss" if Redis is down: reads fall back to
                # PostgreSQL, writes to the cache are skipped. Throttling fails open meanwhile.
                "SOCKET_CONNECT_TIMEOUT": 1,
                "SOCKET_TIMEOUT": 1,
                "IGNORE_EXCEPTIONS": True,
            },
        }
    }
    DJANGO_REDIS_LOG_IGNORED_EXCEPTIONS = True  # an outage shows up in the logs, not as 500s
else:
    # No Redis configured (e.g. plain `manage.py runserver`): per-process memory cache.
    CACHES = {"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}}

# --- Celery (background jobs) -------------------------------------------------------
# Broker = Redis DB 0 (DB 1 = cache, DB 2 = tests). Without a broker (plain runserver),
# tasks run inline right after commit, so local development needs no worker.
CELERY_BROKER_URL = env("CELERY_BROKER_URL", default="")
CELERY_TASK_ALWAYS_EAGER = not CELERY_BROKER_URL
CELERY_TASK_IGNORE_RESULT = True          # no result backend: tasks record outcomes in the DB/logs
CELERY_TASK_ACKS_LATE = True              # ack after the task finishes -> redelivered if a worker dies
CELERY_WORKER_PREFETCH_MULTIPLIER = 1     # (safe because tasks are idempotent)
CELERY_BROKER_CONNECTION_RETRY_ON_STARTUP = True

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=15),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=1),
}

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "simple": {"format": "{asctime} {levelname} {name}: {message}", "style": "{"},
    },
    "handlers": {
        "console": {"class": "logging.StreamHandler", "formatter": "simple"},
    },
    "root": {"handlers": ["console"], "level": "INFO"},
}
