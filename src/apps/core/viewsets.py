from django.conf import settings
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from rest_condition import Or
from rest_framework import mixins
from rest_framework.authentication import SessionAuthentication, TokenAuthentication
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet, GenericViewSet

from apps.user.constants import SYSADMIN_GROUP


class AuthViewSet:
    authentication_classes = [SessionAuthentication, TokenAuthentication]
    permission_classes = [Or(IsAuthenticated, )]


class BaseWithoutCreateViewSet(
    AuthViewSet,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    mixins.DestroyModelMixin,
    mixins.ListModelMixin,
    GenericViewSet
):
    pass


@method_decorator(
    cache_page(settings.CACHE_TIMEOUTS["core"], key_prefix="core"),
    name="list"
)
class BaseViewSet(AuthViewSet, ModelViewSet):

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())

        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)


class UserFilteredViewSet(BaseViewSet):
    def get_queryset(self):
        user = self.request.user
        default_queryset = super().get_queryset()

        if user.is_superuser or user.groups.filter(name=SYSADMIN_GROUP):  # Admin access or Application access
            return default_queryset

        # TODO: Use get logged_as to filter
        kwargs = {'user_id': user.id}
        return default_queryset.filter(**kwargs)
