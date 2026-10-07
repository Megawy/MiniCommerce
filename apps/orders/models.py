from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models

from apps.products.models import Product


class Order(models.Model):
    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        PAID = "PAID", "Paid"
        CANCELLED = "CANCELLED", "Cancelled"
        COMPLETED = "COMPLETED", "Completed"

    # PROTECT: orders are financial records; deactivate a user instead of deleting them.
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="orders")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    # Stored, not derived: it's what the customer was charged. Set once at checkout (Phase 6).
    total = models.DecimalField(max_digits=12, decimal_places=2, default=0, validators=[MinValueValidator(0)])
    # Set once by the background confirmation task (idempotency marker). Not exposed in the API.
    confirmation_sent_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.CheckConstraint(condition=models.Q(total__gte=0), name="order_total_non_negative"),
        ]

    def __str__(self):
        return f"Order #{self.pk} ({self.status})"


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items")
    # PROTECT + NOT NULL: an ordered product can't be deleted, only deactivated (is_active=False).
    product = models.ForeignKey(Product, on_delete=models.PROTECT, related_name="order_items")
    quantity = models.PositiveIntegerField()
    # Snapshot of Product.price at purchase time. Never read Product.price for history.
    price = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["id"]
        constraints = [
            models.CheckConstraint(condition=models.Q(quantity__gt=0), name="order_item_quantity_positive"),
            models.CheckConstraint(condition=models.Q(price__gte=0), name="order_item_price_non_negative"),
        ]

    def __str__(self):
        return f"{self.product} × {self.quantity} @ {self.price}"

    @property
    def subtotal(self):
        return self.price * self.quantity  # snapshot price, not product.price
