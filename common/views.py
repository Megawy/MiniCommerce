import logging

from django.db import DatabaseError, connection
from drf_spectacular.utils import extend_schema, inline_serializer
from rest_framework import serializers
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

logger = logging.getLogger(__name__)


HEALTH = inline_serializer("Health", fields={
    "status": serializers.ChoiceField(choices=["ok", "error"]),
    "database": serializers.ChoiceField(choices=["ok", "unreachable"]),
})


@extend_schema(
    summary="Health check",
    description="Liveness plus a `SELECT 1` against PostgreSQL. Public.",
    responses={200: HEALTH, 503: HEALTH},
    tags=["health"],
)
@api_view(["GET"])
@permission_classes([AllowAny])
def health(request):
    """Liveness + database check."""
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
        db_ok = True
    except DatabaseError:
        logger.exception("Health check: database unreachable")
        db_ok = False

    return Response(
        {"status": "ok" if db_ok else "error", "database": "ok" if db_ok else "unreachable"},
        status=status.HTTP_200_OK if db_ok else status.HTTP_503_SERVICE_UNAVAILABLE,
    )
