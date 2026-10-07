from django.contrib import admin

# Branding for the built-in admin site (no theme, just titles).
admin.site.site_header = "MiniCommerce back-office"
admin.site.site_title = "MiniCommerce admin"
admin.site.index_title = "Administration"


class ReadOnlyHistoryMixin:
    """For records that represent business history (orders, line items, payments).

    They are created only by checkout; the admin may view them but never add or delete them.
    Combine with has_change_permission() -> False for fully view-only screens.
    """

    def has_add_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
