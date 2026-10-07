from django.db import models

from apps.orders.models import Order


class Payment(models.Model):
    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        SUCCESS = "SUCCESS", "Success"
        FAILED = "FAILED", "Failed"

    # OneToOne -> UNIQUE(order_id): one payment per order in this simple project.
    order = models.OneToOneField(Order, on_delete=models.PROTECT, related_name="payment")
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    # NULL until the provider returns one; UNIQUE ignores NULLs in Postgres.
    transaction_id = models.CharField(max_length=64, unique=True, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.CheckConstraint(condition=models.Q(amount__gte=0), name="payment_amount_non_negative"),
        ]

    def __str__(self):
        return f"Payment for order #{self.order_id} ({self.status})"
