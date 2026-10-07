from rest_framework import serializers

from .models import Category, Product


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ["id", "name", "slug", "created_at", "updated_at"]
        read_only_fields = ["id", "created_at", "updated_at"]


class CategorySummarySerializer(serializers.ModelSerializer):
    """Small nested representation used inside product responses."""

    class Meta:
        model = Category
        fields = ["id", "name", "slug"]


class ProductSerializer(serializers.ModelSerializer):
    # Read: nested object.  Write: plain id.  Both map to the same model field.
    category = CategorySummarySerializer(read_only=True)
    category_id = serializers.PrimaryKeyRelatedField(
        source="category", queryset=Category.objects.all(), write_only=True
    )

    class Meta:
        model = Product
        fields = [
            "id", "name", "slug", "description", "price", "stock", "is_active",
            "category", "category_id", "created_at", "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]
