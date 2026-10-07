from django.db.models import Prefetch
from drf_spectacular.utils import OpenApiExample, OpenApiResponse, extend_schema, extend_schema_view
from rest_framework import status, viewsets
from rest_framework.response import Response
from rest_framework.views import APIView

from common.openapi import VALIDATION_ERROR, errors

from .models import Cart, CartItem
from .serializers import (
    AddCartItemSerializer,
    CartItemSerializer,
    CartSerializer,
    UpdateCartItemSerializer,
)


def get_cart(user, with_items=False):
    """The user's cart, created on first access."""
    qs = Cart.objects.all()
    if with_items:
        # Cart --(1 query)--> items JOIN product  => 2 queries total, regardless of item count.
        qs = qs.prefetch_related(
            Prefetch("items", queryset=CartItem.objects.select_related("product"))
        )
    cart, _ = qs.get_or_create(user=user)
    return cart


class CartView(APIView):
    """GET /api/cart/  and  DELETE /api/cart/ (clear)."""

    @extend_schema(
        summary="Get my cart",
        description="The authenticated user's cart (created on first access). `total` is derived "
                    "from current product prices; nothing is reserved until checkout.",
        responses={200: CartSerializer, **errors(401)},
    )
    def get(self, request):
        return Response(CartSerializer(get_cart(request.user, with_items=True)).data)

    @extend_schema(summary="Clear my cart", description="Removes all items; the cart itself remains.",
                   responses={204: None, **errors(401)})
    def delete(self, request):
        get_cart(request.user).items.all().delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


@extend_schema_view(
    create=extend_schema(
        summary="Add a product to my cart",
        description="If the product is already in the cart, the quantity is **added** to the "
                    "existing line (200) instead of creating a new one (201). The resulting quantity "
                    "must not exceed stock and the product must be active.",
        request=AddCartItemSerializer,
        responses={
            201: OpenApiResponse(CartItemSerializer, description="New cart line."),
            200: OpenApiResponse(CartItemSerializer, description="Merged into an existing line."),
            400: VALIDATION_ERROR,
            **errors(401, 404, 409, e404="Product not found.",
                     e409="Concurrent add of the same product; retry."),
        },
        examples=[OpenApiExample("Add two", request_only=True, value={"product_id": 5, "quantity": 2})],
    ),
    partial_update=extend_schema(
        summary="Change quantity of a cart line",
        description="Only `quantity` can change. Must be ≥ 1 and ≤ current stock.",
        request=UpdateCartItemSerializer,
        responses={200: CartItemSerializer, 400: VALIDATION_ERROR, **errors(401, 404)},
    ),
    destroy=extend_schema(summary="Remove a cart line", responses={204: None, **errors(401, 404)}),
)
class CartItemViewSet(viewsets.GenericViewSet):
    """POST /api/cart/items/, PATCH + DELETE /api/cart/items/{id}/."""

    serializer_class = CartItemSerializer

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):  # schema generation: no real user
            return CartItem.objects.none()
        # Ownership is enforced HERE: another user's item id simply isn't found -> 404.
        return CartItem.objects.filter(cart__user=self.request.user).select_related("product")

    def create(self, request):
        serializer = AddCartItemSerializer(data=request.data, context={"cart": get_cart(request.user)})
        serializer.is_valid(raise_exception=True)
        item, created = serializer.save()
        return Response(
            CartItemSerializer(item).data,
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )

    def partial_update(self, request, pk=None):
        item = self.get_object()
        serializer = UpdateCartItemSerializer(item, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(CartItemSerializer(item).data)

    def destroy(self, request, pk=None):
        self.get_object().delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
