from django.db import IntegrityError
from rest_framework import status
from rest_framework.response import Response


class IdempotencyModelViewSetMixin:
    def create(self, request, *args, **kwargs):
        try:
            # noinspection PyUnresolvedReferences
            response = super().create(request, *args, **kwargs)
        except IntegrityError as exc:
            if 'unique constraint' not in str(exc):
                raise exc
            return Response({}, status=status.HTTP_304_NOT_MODIFIED)
        return response
