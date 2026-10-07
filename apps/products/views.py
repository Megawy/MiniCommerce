from django.core.cache import cache
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import OpenApiParameter, extend_schema, extend_schema_view
from rest_framework import filters, viewsets

from common.openapi import PUBLIC, VALIDATION_ERROR, errors
from common.permissions import IsAdminOrReadOnly

from .cache import CATEGORY_LIST_KEY, CATEGORY_LIST_TTL
from .filters import ProductFilter
from .models import Category, Product
from .serializers import CategorySerializer, ProductSerializer


WRITE_ERRORS = {400: VALIDATION_ERROR, **errors(401, 403)}


@extend_schema_view(
    list=extend_schema(
        summary="List categories",
        description="Public. Served from a short-lived shared cache (≤ 60 s); writes invalidate it.",
        auth=PUBLIC,
    ),
    retrieve=extend_schema(summary="Get a category", auth=PUBLIC, responses={200: CategorySerializer, **errors(404)}),
    create=extend_schema(summary="Create a category (staff)", responses={201: CategorySerializer, **WRITE_ERRORS}),
    update=extend_schema(summary="Replace a category (staff)", responses={200: CategorySerializer, **WRITE_ERRORS, **errors(404)}),
    partial_update=extend_schema(summary="Update a category (staff)", responses={200: CategorySerializer, **WRITE_ERRORS, **errors(404)}),
    destroy=extend_schema(
        summary="Delete a category (staff)",
        responses={204: None, **errors(401, 403, 404, 409, e409="The category still has products.")},
    ),
)
class CategoryViewSet(viewsets.ModelViewSet):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    permission_classes = [IsAdminOrReadOnly]

    def list(self, request, *args, **kwargs):
        # Cache the serialized *data* (same for every caller), not the HTTP response:
        # pagination still runs per request, so ?page / ?page_size and the absolute
        # next/previous links are always correct for this request.
        data = cache.get(CATEGORY_LIST_KEY)
        if data is None:  # miss, expired, or Redis unavailable -> PostgreSQL
            data = [dict(row) for row in self.get_serializer(self.get_queryset(), many=True).data]
            cache.set(CATEGORY_LIST_KEY, data, CATEGORY_LIST_TTL)
        page = self.paginate_queryset(data)
        return self.get_paginated_response(page)


@extend_schema_view(
    list=extend_schema(
        summary="List products",
        description="Public. Inactive products are only visible to staff. Supports filtering "
                    "(`category` slug, `is_active`, `min_price`, `max_price`), `search` (name, "
                    "description), `ordering` (`price`, `created_at`, `name`, prefix `-` for desc; "
                    "default `-created_at`) and pagination (`page`, `page_size` ≤ 100, default 20).",
        auth=PUBLIC,
        parameters=[OpenApiParameter(  # same name as OrderingFilter's param -> replaces it with an enum
            "ordering", str, enum=["price", "-price", "created_at", "-created_at", "name", "-name"],
            description="Sort order. Default `-created_at`.")],
    ),
    retrieve=extend_schema(summary="Get a product", auth=PUBLIC, responses={200: ProductSerializer, **errors(404)}),
    create=extend_schema(
        summary="Create a product (staff)",
        description="Write with `category_id`; responses embed the `category` object.",
        responses={201: ProductSerializer, **WRITE_ERRORS},
    ),
    update=extend_schema(summary="Replace a product (staff)", responses={200: ProductSerializer, **WRITE_ERRORS, **errors(404)}),
    partial_update=extend_schema(summary="Update a product (staff)", responses={200: ProductSerializer, **WRITE_ERRORS, **errors(404)}),
    destroy=extend_schema(
        summary="Delete a product (staff)",
        description="Products that appear in orders are protected — deactivate them instead (`is_active=false`).",
        responses={204: None, **errors(401, 403, 404, 409, e409="The product is referenced by orders.")},
    ),
)
class ProductViewSet(viewsets.ModelViewSet):
    serializer_class = ProductSerializer
    permission_classes = [IsAdminOrReadOnly]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_class = ProductFilter
    search_fields = ["name", "description"]
    ordering_fields = ["price", "created_at", "name"]  # whitelist
    ordering = ["-created_at"]                         # default

    def get_queryset(self):
        # One JOIN instead of one extra query per product for `category`.
        qs = Product.objects.select_related("category")
        if not self.request.user.is_staff:
            qs = qs.filter(is_active=True)  # customers never see deactivated products
        return qs
