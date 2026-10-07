from django.conf import settings
from django.db import models

from apps.products.models import Product


class Cart(models.Model):
    # OneToOne = ForeignKey + UNIQUE: exactly one cart per user, enforced by Postgres.
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="cart"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Cart of {self.user}"

    @property
    def total(self):
        # Derived, never stored. Uses the prefetched items when available (no extra query).
        return sum((item.subtotal for item in self.items.all()), start=0)


class CartItem(models.Model):
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name="items")
    # CASCADE: if a product is deleted, it simply disappears from carts.
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="cart_items")
    quantity = models.PositiveIntegerField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["id"]
        constraints = [
            models.UniqueConstraint(fields=["cart", "product"], name="unique_product_per_cart"),
            # PositiveIntegerField allows 0; a cart line of 0 makes no sense.
            models.CheckConstraint(condition=models.Q(quantity__gt=0), name="cart_item_quantity_positive"),
        ]

    def __str__(self):
        return f"{self.product} × {self.quantity}"

    @property
    def subtotal(self):
        return self.product.price * self.quantity
