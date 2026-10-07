"""python manage.py seed_demo [--reset] [--password ...]

Creates a small, predictable demo dataset straight through the ORM (no HTTP, no API).
Demo records are identified by fixed emails, slugs and payment transaction ids, so the
command is idempotent and --reset never touches anything else.
"""
import os
from decimal import Decimal

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.cart.models import Cart, CartItem
from apps.orders.models import Order, OrderItem
from apps.payments.models import Payment
from apps.products.models import Category, Product

User = get_user_model()

DEFAULT_DEV_PASSWORD = "demo-password-123"  # development only; never used when DEBUG=False

USERS = [
    {"email": "admin@example.com", "first_name": "Ada", "last_name": "Admin", "is_staff": True, "is_superuser": True},
    {"email": "jane@example.com", "first_name": "Jane", "last_name": "Doe"},
    {"email": "bob@example.com", "first_name": "Bob", "last_name": "Smith"},
]

CATEGORIES = [
    ("keyboards", "Keyboards"),
    ("mice", "Mice"),
    ("monitors", "Monitors"),
    ("headsets", "Headsets"),
]

# slug: (name, category slug, price, stock, is_active, description)
PRODUCTS = {
    "mechanical-keyboard": ("Mechanical Keyboard", "keyboards", "99.99", 25, True, "Hot-swappable switches, aluminium case."),
    "wireless-keyboard": ("Wireless Keyboard", "keyboards", "49.90", 40, True, "Low-profile, Bluetooth and 2.4 GHz."),
    "wireless-mouse": ("Wireless Mouse", "mice", "29.99", 60, True, "Ergonomic, 70-day battery."),
    "gaming-mouse": ("Gaming Mouse", "mice", "59.00", 30, True, "26K DPI sensor, 58 g."),
    "4k-monitor-27": ('27" 4K Monitor', "monitors", "349.00", 10, True, "IPS, USB-C 90 W."),
    "gaming-monitor-24": ('24" Gaming Monitor', "monitors", "199.00", 15, True, "165 Hz, 1 ms."),
    "usb-headset": ("USB Headset", "headsets", "39.50", 35, True, "Noise-cancelling mic."),
    "retro-headset": ("Retro Headset", "headsets", "19.99", 0, False, "Discontinued (inactive demo product)."),
}

CART = {"owner": "bob@example.com", "lines": [("mechanical-keyboard", 1), ("wireless-mouse", 2)]}

# The payment transaction id is the stable key that marks an order as demo data.
ORDERS = [
    {"txn": "demo_txn_0001", "owner": "jane@example.com", "status": Order.Status.PAID,
     "lines": [("mechanical-keyboard", 1), ("usb-headset", 2)]},
    {"txn": "demo_txn_0002", "owner": "jane@example.com", "status": Order.Status.COMPLETED,
     "lines": [("4k-monitor-27", 1)]},
]


class Command(BaseCommand):
    help = "Create (or with --reset, restore) development demo data. Safe to run repeatedly."

    def add_arguments(self, parser):
        parser.add_argument("--reset", action="store_true",
                            help="Restore demo records to their initial state (other data is untouched).")
        parser.add_argument("--password",
                            help="Password for demo users (default: $DEMO_PASSWORD or a dev-only default).")

    def handle(self, *args, **options):
        password = options["password"] or os.environ.get("DEMO_PASSWORD")
        if not settings.DEBUG and not password:
            raise CommandError("Refusing to use the default demo password with DEBUG=False. Pass --password.")
        password = password or DEFAULT_DEV_PASSWORD
        reset = options["reset"]

        # One transaction for the whole seed: any failure leaves the database untouched.
        with transaction.atomic():
            if reset:
                self.delete_demo_orders()
            users = self.seed_users(password, reset)
            products = self.seed_catalog(reset)
            self.seed_cart(users, products, reset)
            self.seed_orders(users, products)

        self.print_summary(reset)

    # --- steps ------------------------------------------------------------

    def delete_demo_orders(self):
        txns = [o["txn"] for o in ORDERS]
        # Materialise the ids first: QuerySets are lazy, and once the payments are gone a
        # `filter(payment__transaction_id__in=...)` would match nothing.
        order_ids = list(Order.objects.filter(payment__transaction_id__in=txns).values_list("id", flat=True))
        Payment.objects.filter(transaction_id__in=txns).delete()  # Payment -> Order is PROTECT
        Order.objects.filter(id__in=order_ids).delete()            # cascades to OrderItems

    def seed_users(self, password, reset):
        users = {}
        for data in USERS:
            data = data.copy()
            email = data.pop("email")
            user = User.objects.filter(email=email).first()
            if user is None:
                user = User.objects.create_user(email=email, password=password, **data)
            elif reset:
                for field, value in data.items():
                    setattr(user, field, value)
                user.set_password(password)
                user.save()
            users[email] = user
        return users

    def seed_catalog(self, reset):
        # get_or_create = "INSERT if missing"; update_or_create = "make it look like this".
        sync = "update_or_create" if reset else "get_or_create"
        categories = {
            slug: getattr(Category.objects, sync)(slug=slug, defaults={"name": name})[0]
            for slug, name in CATEGORIES
        }
        products = {}
        for slug, (name, cat, price, stock, active, desc) in PRODUCTS.items():
            products[slug], _ = getattr(Product.objects, sync)(slug=slug, defaults={
                "name": name, "category": categories[cat], "price": Decimal(price),
                "stock": stock, "is_active": active, "description": desc,
            })
        return products

    def seed_cart(self, users, products, reset):
        cart, _ = Cart.objects.get_or_create(user=users[CART["owner"]])
        sync = "update_or_create" if reset else "get_or_create"
        for slug, quantity in CART["lines"]:
            # (cart, product) is the UniqueConstraint, so this can never duplicate a line.
            getattr(CartItem.objects, sync)(cart=cart, product=products[slug], defaults={"quantity": quantity})

    def seed_orders(self, users, products):
        for spec in ORDERS:
            if Payment.objects.filter(transaction_id=spec["txn"]).exists():
                continue  # already seeded
            lines = [(products[slug], qty) for slug, qty in spec["lines"]]
            total = sum((p.price * qty for p, qty in lines), start=Decimal("0"))
            order = Order.objects.create(user=users[spec["owner"]], status=spec["status"], total=total)
            OrderItem.objects.bulk_create(
                # price = snapshot of the product price at "purchase" time
                OrderItem(order=order, product=p, quantity=qty, price=p.price) for p, qty in lines
            )
            self.create_payment(order, spec["txn"])

    def create_payment(self, order, txn):
        Payment.objects.create(order=order, amount=order.total, status=Payment.Status.SUCCESS, transaction_id=txn)

    # --- output -----------------------------------------------------------

    def print_summary(self, reset):
        demo_orders = Order.objects.filter(payment__transaction_id__in=[o["txn"] for o in ORDERS])
        out = self.stdout.write
        out(self.style.MIGRATE_HEADING("MiniCommerce demo data" + (" (reset)" if reset else "")))
        out("----------------------")
        out("Users:")
        for data in USERS:
            out(f"  {data['email']}" + ("  [staff]" if data.get("is_staff") else ""))
        out(f"Categories: {Category.objects.filter(slug__in=[s for s, _ in CATEGORIES]).count()}")
        out(f"Products:   {Product.objects.filter(slug__in=PRODUCTS).count()}")
        out(f"Cart items: {CartItem.objects.filter(cart__user__email=CART['owner']).count()} ({CART['owner']})")
        out(f"Orders:     {demo_orders.count()}")
        out(f"Payments:   {Payment.objects.filter(order__in=demo_orders).count()}")
        out(self.style.SUCCESS("Demo data ready."))
