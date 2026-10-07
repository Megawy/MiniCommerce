"""Catalog cache: key + TTL in one place (used by the view and the invalidation signal)."""

# Full Redis key: "minicommerce:1:catalog:categories:v1" (KEY_PREFIX + Django key version + key).
# Bump "v1" if the cached data shape (CategorySerializer fields) ever changes.
CATEGORY_LIST_KEY = "catalog:categories:v1"
CATEGORY_LIST_TTL = 60  # seconds — bounds staleness even if an invalidation is ever missed
