from .base import *  # noqa: F401,F403
from .base import MIDDLEWARE, env

DEBUG = False

# Static files: `collectstatic` runs at image build time; WhiteNoise serves them from Gunicorn
# (no nginx needed yet). Hashed + compressed file names allow long browser caching.
_i = MIDDLEWARE.index("django.middleware.security.SecurityMiddleware") + 1
MIDDLEWARE = [*MIDDLEWARE[:_i], "whitenoise.middleware.WhiteNoiseMiddleware", *MIDDLEWARE[_i:]]
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"},
}

SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True

# HTTPS hardening (`manage.py check --deploy`). Env-driven so a local/Docker run can opt out.
SECURE_SSL_REDIRECT = env.bool("SECURE_SSL_REDIRECT", default=True)
# Enable only once the domain is HTTPS-only for good: browsers cache HSTS (e.g. 31536000).
SECURE_HSTS_SECONDS = env.int("SECURE_HSTS_SECONDS", default=0)
