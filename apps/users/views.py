from drf_spectacular.utils import OpenApiExample, extend_schema
from rest_framework import generics
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.throttling import ScopedRateThrottle
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework_simplejwt.views import TokenObtainPairView

from common.openapi import VALIDATION_ERROR, errors

from .serializers import RegisterSerializer, UserSerializer


@extend_schema(
    summary="Register a customer account",
    description="Creates a user. Passwords are validated by Django's password validators and "
                "stored hashed; the response never contains the password. Public, throttled.",
    responses={201: RegisterSerializer, 400: VALIDATION_ERROR, **errors(429)},
    examples=[OpenApiExample("Register", request_only=True, value={
        "email": "user@example.com", "password": "StrongPassword123",
        "first_name": "John", "last_name": "Doe"})],
)
class RegisterView(generics.CreateAPIView):
    serializer_class = RegisterSerializer
    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "auth"


@extend_schema(
    summary="Log in (obtain JWT pair)",
    description="Exchange email + password for an `access` token (15 min) and a `refresh` token "
                "(1 day). Send the access token as `Authorization: Bearer <access>`. Public, throttled.",
    responses={200: TokenObtainPairSerializer, 400: VALIDATION_ERROR,
               **errors(401, 429, e401="Wrong email/password or inactive account.")},
    examples=[OpenApiExample("Login", request_only=True,
                             value={"email": "user@example.com", "password": "StrongPassword123"})],
)
class LoginView(TokenObtainPairView):
    """SimpleJWT's login, unchanged except for brute-force throttling."""

    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "auth"


@extend_schema(summary="Current user", responses={200: UserSerializer, **errors(401)})
class MeView(generics.RetrieveAPIView):
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        return self.request.user
