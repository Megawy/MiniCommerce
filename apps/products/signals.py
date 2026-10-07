"""Invalidate the category-list cache on any write — API, Admin, shell or seed_demo."""
from django.core.cache import cache
from django.db import transaction
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from .cache import CATEGORY_LIST_KEY
from .models import Category


@receiver([post_save, post_delete], sender=Category)
def invalidate_category_list(sender, **kwargs):
    # After COMMIT, so a concurrent reader can't re-cache the pre-commit rows after we delete.
    transaction.on_commit(lambda: cache.delete(CATEGORY_LIST_KEY))
