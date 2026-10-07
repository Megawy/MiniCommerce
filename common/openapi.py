"""Shared OpenAPI pieces (drf-spectacular). Documentation only — no runtime behaviour."""
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiResponse, inline_serializer
from rest_framework import serializers

# The API's one error shape for non-field errors: {"detail": "..."}.
ERROR = inline_serializer("Error", fields={"detail": serializers.CharField()})

# Security for public reads behind IsAdminOrReadOnly: anonymous OR Bearer token.
# (drf-spectacular only auto-detects this for DRF's own AllowAny / IsAuthenticatedOrReadOnly.)
PUBLIC = [{}, {"jwtAuth": []}]

_DESCRIPTIONS = {
    400: "Business rule violated.",
    401: "Missing, invalid or expired access token.",
    403: "Authenticated, but not allowed (staff only).",
    404: "Not found — or not yours (other users' objects are invisible).",
    409: "Conflict with existing data.",
    429: "Too many requests (auth endpoints: 10/minute).",
}

VALIDATION_ERROR = OpenApiResponse(
    OpenApiTypes.OBJECT, description='Validation error: `{"<field>": ["message", ...]}`.'
)


def errors(*codes, **descriptions):
    """{code: OpenApiResponse(Error)} for the given status codes. Override text with e.g. e404='...'."""
    return {
        code: OpenApiResponse(ERROR, description=descriptions.get(f"e{code}", _DESCRIPTIONS[code]))
        for code in codes
    }
