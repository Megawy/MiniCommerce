from django.contrib import admin

from common.admin import ReadOnlyHistoryMixin

from .models import Payment


@admin.register(Payment)
class PaymentAdmin(ReadOnlyHistoryMixin, admin.ModelAdmin):
    """Transaction history: view-only. No buttons that change payment state."""

    list_display = ["id", "order", "customer", "amount", "status", "transaction_id", "created_at"]
    list_filter = ["status", "created_at"]
    list_select_related = ["order__user"]
    search_fields = ["transaction_id", "=order__id", "order__user__email"]
    date_hierarchy = "created_at"
    ordering = ["-created_at"]

    def has_change_permission(self, request, obj=None):
        return False

    @admin.display(description="Customer", ordering="order__user__email")
    def customer(self, obj):
        return obj.order.user.email
