from django.contrib import admin
from django.db.models import Count, DecimalField, F, Sum

from .models import Cart, CartItem


class CartItemInline(admin.TabularInline):
    model = CartItem
    extra = 0
    fields = ["product", "quantity", "subtotal", "created_at"]
    readonly_fields = ["subtotal", "created_at"]
    autocomplete_fields = ["product"]

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("product")


@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    """Support/debugging view of customers' carts. Totals are computed, never stored."""

    list_display = ["id", "user", "item_count", "created_at", "updated_at"]
    list_select_related = ["user"]
    search_fields = ["user__email"]  # also powers CartItem.cart autocomplete
    autocomplete_fields = ["user"]
    readonly_fields = ["current_total", "created_at", "updated_at"]
    ordering = ["-updated_at"]
    inlines = [CartItemInline]

    def get_queryset(self, request):
        return super().get_queryset(request).annotate(_item_count=Count("items"))

    @admin.display(description="Items", ordering="_item_count")
    def item_count(self, obj):
        return obj._item_count

    @admin.display(description="Total (current prices)")
    def current_total(self, obj):
        # One SUM query; Cart.total would load every product row one by one.
        result = obj.items.aggregate(
            total=Sum(F("product__price") * F("quantity"), output_field=DecimalField())
        )["total"]
        return result or 0


@admin.register(CartItem)
class CartItemAdmin(admin.ModelAdmin):
    list_display = ["id", "cart", "product", "quantity", "created_at"]
    list_filter = ["product__category", "created_at"]
    list_select_related = ["cart__user", "product"]
    search_fields = ["cart__user__email", "product__name"]
    autocomplete_fields = ["cart", "product"]
    readonly_fields = ["created_at", "updated_at"]
    ordering = ["-created_at"]
