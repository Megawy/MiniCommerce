# Load the Celery app whenever Django starts, so @shared_task binds to it
# and web processes can enqueue tasks.
from .celery import app as celery_app

__all__ = ("celery_app",)
