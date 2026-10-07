from django.contrib import admin
from django.db.models import Count
from django.urls import reverse
from django.utils.html import format_html

from common.admin import ReadOnlyHistoryMixin

from .models import Order, OrderItem


class OrderItemInline(ReadOnlyHistoryMixin, admin.TabularInline):
    model = OrderItem
    extra = 0
    fields = ["product", "quantity", "price", "subtotal", "created_at"]
    readonly_fields = fields  # price = purchase-time snapshot, never Product.price
    verbose_name_plural = "Items (price = snapshot at checkout)"

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("product")


class PaymentStatusFilter(admin.ChoicesFieldListFilter):
    """Payment.status is also called "status": give its sidebar filter a distinct title."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.title = "payment status"


@admin.register(Order)
class OrderAdmin(ReadOnlyHistoryMixin, admin.ModelAdmin):
    list_display = ["id", "user", "status", "total", "item_count", "payment_status", "created_at", "updated_at"]
    list_filter = ["status", ("payment__status", PaymentStatusFilter), "created_at"]
    list_select_related = ["user", "payment"]  # reverse OneToOne works with select_related
    search_fields = ["=id", "user__email"]       # "=id": exact match on the order number
    date_hierarchy = "created_at"
    ordering = ["-created_at"]
    # Only `status` stays editable (operational: mark COMPLETED/CANCELLED). Changing it has no
    # side effects (no restock, no refund) — the domain doesn't define those yet.
    readonly_fields = ["user", "total", "payment_link", "confirmation_sent_at", "created_at", "updated_at"]
    fieldsets = [
        (None, {"fields": ["user", "status", "total", "payment_link", "confirmation_sent_at"]}),
        ("Timestamps", {"fields": ["created_at", "updated_at"]}),
    ]
    inlines = [OrderItemInline]

    def get_queryset(self, request):
        return super().get_queryset(request).annotate(_item_count=Count("items"))

    @admin.display(description="Items", ordering="_item_count")
    def item_count(self, obj):
        return obj._item_count

    @admin.display(description="Payment", ordering="payment__status")
    def payment_status(self, obj):
        payment = getattr(obj, "payment", None)  # reverse OneToOne raises if missing
        return payment.status if payment else "—"

    @admin.display(description="Payment")
    def payment_link(self, obj):
        payment = getattr(obj, "payment", None)
        if payment is None:
            return "—"
        url = reverse("admin:payments_payment_change", args=[payment.pk])
        return format_html('<a href="{}">{} · {} · {}</a>', url, payment.status, payment.amount, payment.transaction_id)


@admin.register(OrderItem)
class OrderItemAdmin(ReadOnlyHistoryMixin, admin.ModelAdmin):
    list_display = ["id", "order", "product", "quantity", "price", "subtotal", "created_at"]
    list_filter = ["order__status", "product__category", "created_at"]
    list_select_related = ["order", "product"]
    search_fields = ["=order__id", "product__name", "order__user__email"]
    ordering = ["-created_at"]

    def has_change_permission(self, request, obj=None):
        return False  # view-only: line items never change after checkout
