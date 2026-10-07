"""Celery application: `celery -A config worker` loads this module.

Same code, settings and database as the web app; only the entry point differs:
HTTP request -> Gunicorn -> Django   vs   Redis message -> Celery worker -> task.
"""
import os

from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.prod")  # same default as wsgi.py

app = Celery("minicommerce")
# Every Django setting prefixed CELERY_ configures Celery (CELERY_BROKER_URL -> broker_url, ...).
app.config_from_object("django.conf:settings", namespace="CELERY")
# Import tasks.py from every installed app (apps/orders/tasks.py, ...).
app.autodiscover_tasks()
