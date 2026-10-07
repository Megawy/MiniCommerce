import logging

from django.db import IntegrityError
from django.db.models import ProtectedError
from psycopg import errors as pg_errors
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import exception_handler, set_rollback

logger = logging.getLogger(__name__)


def api_exception_handler(exc, context):
    """DRF's default handler plus two database conflicts that would otherwise be a 500.

    - on_delete=PROTECT violation           -> 409
    - UNIQUE violation that slipped past the serializer (e.g. a double-click race) -> 409
    Any other IntegrityError is a bug and stays a 500.
    """
    if isinstance(exc, ProtectedError):
        return Response(
            {"detail": "This object is referenced by other records and cannot be deleted."},
            status=status.HTTP_409_CONFLICT,
        )
    if isinstance(exc, IntegrityError) and isinstance(exc.__cause__, pg_errors.UniqueViolation):
        logger.warning("Unique violation in %s: %s", context["view"].__class__.__name__, exc)
        set_rollback()  # same as DRF does for its own exceptions
        return Response(
            {"detail": "Conflicting request, please retry."},  # no SQL details leaked
            status=status.HTTP_409_CONFLICT,
        )
    return exception_handler(exc, context)
