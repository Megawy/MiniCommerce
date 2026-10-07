from django.db.models import Prefetch
from drf_spectacular.utils import OpenApiExample, extend_schema, extend_schema_view
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.payments.services import PaymentFailed
from common.openapi import errors

from .models import Order, OrderItem
from .serializers import OrderDetailSerializer, OrderListSerializer
from . import services


@extend_schema_view(
    list=extend_schema(summary="List my orders", description="Newest first. Paginated.",
                       responses={200: OrderListSerializer(many=True), **errors(401)}),
    retrieve=extend_schema(summary="Get one of my orders",
                           description="Includes items with the price paid at checkout (snapshot).",
                           responses={200: OrderDetailSerializer, **errors(401, 404)}),
)
class OrderViewSet(viewsets.ReadOnlyModelViewSet):
    """GET /api/orders/ and /api/orders/{id}/. Orders are created by checkout, never via CRUD."""

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):  # schema generation: no real user
            return Order.objects.none()
        # Ownership: always scoped to the caller, so another user's id -> 404.
        qs = Order.objects.filter(user=self.request.user)
        if self.action in ("retrieve", "checkout"):
            qs = qs.prefetch_related(
                Prefetch("items", queryset=OrderItem.objects.select_related("product"))
            )
        return qs

    def get_serializer_class(self):
        return OrderListSerializer if self.action == "list" else OrderDetailSerializer

    @extend_schema(
        summary="Check out my cart",
        description=(
            "Turns the authenticated user's cart into an order in **one database transaction**:\n\n"
            "1. lock the cart and its product rows (`SELECT ... FOR UPDATE`)\n"
            "2. validate: cart not empty, products active, quantity ≤ stock\n"
            "3. create the order and its items with a **price snapshot**; total computed server-side\n"
            "4. deduct stock\n"
            "5. process the mock payment\n"
            "6. mark the order `PAID` and clear the cart\n\n"
            "No request body: everything comes from the cart. If any step fails, nothing is "
            "changed (no order, no payment, stock and cart untouched)."
        ),
        request=None,
        responses={
            201: OrderDetailSerializer,
            **errors(400, 401, e400="Empty cart, inactive product, insufficient stock or payment declined."),
        },
        examples=[
            OpenApiExample("Empty cart", value={"detail": "Your cart is empty."},
                           response_only=True, status_codes=["400"]),
            OpenApiExample("Insufficient stock", response_only=True, status_codes=["400"], value={
                "detail": "Insufficient stock for Mechanical Keyboard. Available: 2, requested: 5."}),
            OpenApiExample("Payment declined", value={"detail": "Payment declined."},
                           response_only=True, status_codes=["400"]),
        ],
    )
    @action(detail=False, methods=["post"])
    def checkout(self, request):
        """POST /api/orders/checkout/ — no body; everything comes from the user's cart."""
        try:
            order = services.checkout(request.user)
        except (services.CheckoutError, PaymentFailed) as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        order = self.get_queryset().get(pk=order.pk)  # re-read with items prefetched
        return Response(self.get_serializer(order).data, status=status.HTTP_201_CREATED)
