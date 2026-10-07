from rest_framework import serializers
from rest_framework.exceptions import NotFound

from apps.products.models import Product

from .models import Cart, CartItem


def validate_availability(product, quantity):
    """Shared business rule for add + update. Advisory only: stock is reserved at checkout."""
    if not product.is_active:
        raise serializers.ValidationError({"product_id": "This product is not available."})
    if quantity > product.stock:
        raise serializers.ValidationError(
            {"quantity": f"Only {product.stock} in stock (requested {quantity})."}
        )


# --- Output ---------------------------------------------------------------

class CartProductSerializer(serializers.ModelSerializer):
    class Meta:
        model = Product
        fields = ["id", "name", "slug", "price"]


class CartItemSerializer(serializers.ModelSerializer):
    product = CartProductSerializer(read_only=True)
    subtotal = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)

    class Meta:
        model = CartItem
        fields = ["id", "product", "quantity", "subtotal"]


class CartSerializer(serializers.ModelSerializer):
    items = CartItemSerializer(many=True, read_only=True)
    total = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)

    class Meta:
        model = Cart
        fields = ["id", "items", "total"]


# --- Input ----------------------------------------------------------------

class AddCartItemSerializer(serializers.Serializer):
    """POST {product_id, quantity}. Merges into an existing line for the same product."""

    product_id = serializers.IntegerField()
    quantity = serializers.IntegerField(min_value=1)

    def validate(self, attrs):
        product = Product.objects.filter(pk=attrs["product_id"]).first()
        if product is None:
            raise NotFound("Product not found.")  # not a ValidationError -> propagates as 404

        cart = self.context["cart"]
        existing = cart.items.filter(product=product).first()
        new_quantity = attrs["quantity"] + (existing.quantity if existing else 0)
        validate_availability(product, new_quantity)

        attrs.update(product=product, existing=existing, new_quantity=new_quantity)
        return attrs

    def save(self):
        data = self.validated_data
        item = data["existing"]
        if item:
            item.quantity = data["new_quantity"]
            item.save(update_fields=["quantity", "updated_at"])
            return item, False
        item = CartItem.objects.create(
            cart=self.context["cart"], product=data["product"], quantity=data["new_quantity"]
        )
        return item, True


class UpdateCartItemSerializer(serializers.ModelSerializer):
    """PATCH {quantity}. The product cannot be changed."""

    quantity = serializers.IntegerField(min_value=1)

    class Meta:
        model = CartItem
        fields = ["quantity"]

    def validate_quantity(self, value):
        validate_availability(self.instance.product, value)
        return value
