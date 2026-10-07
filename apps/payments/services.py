import uuid

from .models import Payment


class PaymentFailed(Exception):
    """Raised when the (mock) provider declines the charge."""


def charge(amount):
    """Mock payment provider. Always succeeds; tests monkeypatch this to fail or be slow."""
    return f"mock_{uuid.uuid4().hex}"


def process_payment(order):
    """Create the Payment for an order and charge it. Raises PaymentFailed on decline.

    Called inside the checkout transaction, so on failure the PENDING payment row is
    rolled back together with the order (no FAILED row is kept in this simple version).
    """
    payment = Payment.objects.create(order=order, amount=order.total)
    payment.transaction_id = charge(order.total)
    payment.status = Payment.Status.SUCCESS
    payment.save(update_fields=["transaction_id", "status"])
    return payment
