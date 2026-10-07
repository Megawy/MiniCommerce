from decimal import Decimal

from django.db import transaction

from apps.cart.models import Cart
from apps.payments.services import process_payment
from apps.products.models import Product

from .models import Order, OrderItem
from .tasks import send_order_confirmation


class CheckoutError(Exception):
    """A business rule prevented checkout (empty cart, stock, inactive product)."""


def checkout(user) -> Order:
    """Turn the user's cart into a PAID order. All-or-nothing.

    Any exception inside the atomic block (CheckoutError, PaymentFailed, a DB error)
    rolls back every write: order, items, stock, payment, cart.
    """
    with transaction.atomic():
        # 1. Lock the cart row: a double-submitted checkout waits here, then sees an empty cart.
        cart = Cart.objects.select_for_update().filter(user=user).first()
        if cart is None:
            raise CheckoutError("Your cart is empty.")

        cart_items = list(cart.items.all())
        if not cart_items:
            raise CheckoutError("Your cart is empty.")

        # 2. Lock only this cart's product rows, in a fixed order (pk) to avoid deadlocks.
        #    Stock is read AFTER the lock, so it is the committed, current value.
        products = Product.objects.select_for_update().filter(
            pk__in=[item.product_id for item in cart_items]
        ).order_by("pk").in_bulk()

        # 3. Validate against the locked rows.
        for item in cart_items:
            product = products[item.product_id]
            if not product.is_active:
                raise CheckoutError(f"{product.name} is no longer available.")
            if item.quantity > product.stock:
                raise CheckoutError(
                    f"Insufficient stock for {product.name}. "
                    f"Available: {product.stock}, requested: {item.quantity}."
                )

        # 4. Order + items with the price snapshot; total computed server-side.
        total = sum(
            (products[i.product_id].price * i.quantity for i in cart_items), start=Decimal("0")
        )
        order = Order.objects.create(user=user, status=Order.Status.PENDING, total=total)
        OrderItem.objects.bulk_create([
            OrderItem(order=order, product=products[i.product_id],
                      quantity=i.quantity, price=products[i.product_id].price)
            for i in cart_items
        ])

        # 5. Deduct inventory (rows are locked, so no lost updates).
        for item in cart_items:
            product = products[item.product_id]
            product.stock -= item.quantity
            product.save(update_fields=["stock", "updated_at"])

        # 6. Pay. Raises PaymentFailed -> whole block rolls back.
        process_payment(order)
        order.status = Order.Status.PAID
        order.save(update_fields=["status", "updated_at"])

        # 7. Empty the cart (the Cart row itself stays).
        cart.items.all().delete()

        # 8. Background confirmation, enqueued only AFTER COMMIT (a rollback discards it).
        #    robust=True: if the broker is down, log it — the committed order must not 500.
        transaction.on_commit(lambda: send_order_confirmation.delay(order.pk), robust=True)

    return order
