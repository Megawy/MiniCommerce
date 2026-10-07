from django.contrib import admin
from django.db.models import Count
from django.urls import reverse
from django.utils.html import format_html

from .models import Category, Product

LOW_STOCK = 5


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ["name", "slug", "product_count", "created_at", "updated_at"]
    search_fields = ["name", "slug"]  # also powers Product.category autocomplete
    prepopulated_fields = {"slug": ["name"]}
    readonly_fields = ["created_at", "updated_at"]
    ordering = ["name"]

    def get_queryset(self, request):
        # One GROUP BY query instead of a COUNT per row.
        return super().get_queryset(request).annotate(_product_count=Count("products"))

    @admin.display(description="Products", ordering="_product_count")
    def product_count(self, obj):
        url = reverse("admin:products_product_changelist") + f"?category__id__exact={obj.pk}"
        return format_html('<a href="{}">{}</a>', url, obj._product_count)


class StockLevelFilter(admin.SimpleListFilter):
    title = "stock level"
    parameter_name = "stock_level"

    def lookups(self, request, model_admin):
        return [("out", "Out of stock"), ("low", f"Low (1–{LOW_STOCK - 1})"), ("ok", f"{LOW_STOCK}+")]

    def queryset(self, request, queryset):
        if self.value() == "out":
            return queryset.filter(stock=0)
        if self.value() == "low":
            return queryset.filter(stock__gt=0, stock__lt=LOW_STOCK)
        if self.value() == "ok":
            return queryset.filter(stock__gte=LOW_STOCK)
        return queryset


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ["name", "category", "price", "stock", "is_active", "created_at", "updated_at"]
    list_display_links = ["name"]
    list_filter = ["is_active", StockLevelFilter, "category"]
    # Price/active are safe quick edits. Stock is NOT: the list shows stock as of page load,
    # and saving the row would overwrite sales made since (checkout decrements it).
    list_editable = ["price", "is_active"]
    list_select_related = ["category"]
    search_fields = ["name", "slug", "description"]
    autocomplete_fields = ["category"]
    prepopulated_fields = {"slug": ["name"]}  # uniqueness still enforced by the model form
    readonly_fields = ["created_at", "updated_at"]
    ordering = ["-created_at"]
    fieldsets = [
        (None, {"fields": ["name", "slug", "category", "description"]}),
        ("Pricing & inventory", {
            "fields": ["price", "stock", "is_active"],
            "description": "Price changes never affect existing orders (they store a price snapshot). "
                           "Ordered products can't be deleted — deactivate them instead.",
        }),
        ("Timestamps", {"fields": ["created_at", "updated_at"], "classes": ["collapse"]}),
    ]
