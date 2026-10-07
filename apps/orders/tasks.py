"""Background jobs for orders. Run by the Celery worker, never inside an HTTP request."""
import logging

from celery import shared_task
from django.db import DatabaseError
from django.utils import timezone

from .models import Order

logger = logging.getLogger(__name__)

NOTIFIABLE = [Order.Status.PAID, Order.Status.COMPLETED]


def _mask(email):
    name, _, domain = email.partition("@")
    return f"{name[:1]}***@{domain}"


@shared_task(
    autoretry_for=(DatabaseError,),  # transient DB problems: retry later (safe: see claim below)
    retry_backoff=True,
    max_retries=3,
)
def send_order_confirmation(order_id: int) -> str:
    """Simulated order-confirmation notification (logs instead of sending e-mail).

    Payload is just the id: the task reads the *committed* order from PostgreSQL.
    Idempotent: a conditional UPDATE claims the order once, so duplicate deliveries
    (retries, acks_late redelivery, double enqueue) never notify twice.
    """
    order = Order.objects.select_related("user").filter(pk=order_id).first()
    if order is None:
        logger.warning("order_confirmation skipped: order_id=%s not found", order_id)
        return "missing"
    if order.status not in NOTIFIABLE:
        logger.info("order_confirmation skipped: order_id=%s status=%s", order_id, order.status)
        return "not_paid"

    claimed = Order.objects.filter(
        pk=order_id, status__in=NOTIFIABLE, confirmation_sent_at__isnull=True
    ).update(confirmation_sent_at=timezone.now())
    if not claimed:
        logger.info("order_confirmation skipped: order_id=%s already sent", order_id)
        return "already_sent"

    # A real implementation would send an e-mail here (django.core.mail.send_mail).
    logger.info(
        "order_confirmation sent: order_id=%s user_id=%s to=%s total=%s items=%s",
        order.pk, order.user_id, _mask(order.user.email), order.total, order.items.count(),
    )
    return "sent"
