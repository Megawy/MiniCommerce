from django.urls import path
from rest_framework.routers import SimpleRouter

from .views import CartItemViewSet, CartView

router = SimpleRouter()
router.register("cart/items", CartItemViewSet, basename="cart-item")

urlpatterns = [
    path("cart/", CartView.as_view(), name="cart"),
    *router.urls,
]
