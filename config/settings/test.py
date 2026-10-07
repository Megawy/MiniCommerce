"""Settings for pytest (selected in pytest.ini with --ds).

Same as dev, except that when Redis is configured the tests use their own Redis DB (2), so
`cache.clear()` between tests never wipes the running app's cache/throttle state (DB 1).
"""
from .base import REDIS_URL
from .dev import *  # noqa: F401,F403
from .dev import CACHES

# Tasks run in-process and exceptions propagate: deterministic, no broker, no worker,
# and test orders never reach the real worker's queue.
CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True

if REDIS_URL:
    CACHES["default"]["LOCATION"] = REDIS_URL.rsplit("/", 1)[0] + "/2"
