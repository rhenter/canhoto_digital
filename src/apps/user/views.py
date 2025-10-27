import logging

from celery.utils.log import get_task_logger
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from apps.core.viewsets import BaseViewSet
from .models import User
from .serializers import (
    UserBaseSerializer,
    UserCreateUpdateSerializer,
    UserDetailSerializer, UserPreferenceSerializer
)

logger = logging.getLogger(__name__)


class UserViewSet(BaseViewSet):
    permission_classes = [AllowAny]
    queryset = User.objects.all()
    serializer_class = UserCreateUpdateSerializer
    lookup_field = 'id'
    filterset_fields = ('first_name',)
    search_fields = (
        'first_name',
        'last_name',
        'email',
    )
    ordering_fields = (
        '-date_joined',
        '-name',
        'date_joined',
        'first_name',
    )
    ordering = ('-date_joined',)

    def get_serializer_class(self):
        if self.action == 'retrieve':
            return UserDetailSerializer
        elif self.action == 'list':
            return UserBaseSerializer
        return self.serializer_class

    @action(detail=True, methods=['patch'], serializer_class=UserPreferenceSerializer)
    def preferences(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(UserDetailSerializer(instance).data)
