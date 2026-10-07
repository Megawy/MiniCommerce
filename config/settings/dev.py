from .base import *  # noqa: F401,F403
from .base import CORS_ALLOWED_ORIGINS, REST_FRAMEWORK

DEBUG = True

# Angular dev server (`npm start` in frontend/) unless overridden by CORS_ALLOWED_ORIGINS.
CORS_ALLOWED_ORIGINS = CORS_ALLOWED_ORIGINS or ["http://localhost:4200", "http://127.0.0.1:4200"]

REST_FRAMEWORK["DEFAULT_RENDERER_CLASSES"] = [
    "rest_framework.renderers.JSONRenderer",
    "rest_framework.renderers.BrowsableAPIRenderer",
]
