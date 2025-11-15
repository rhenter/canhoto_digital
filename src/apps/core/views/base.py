import logging

from django.contrib.auth import get_user_model
from django.contrib.auth.views import LoginView
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from ..models import TermsOfService
from ..serializers import TermsOfServiceSerializer
from ..viewsets import BaseViewSet

logger = logging.getLogger(__name__)

User = get_user_model()


class CustomLoginView(LoginView):
    template_name = "login.html"


class HealthCheckView(APIView):
    http_method_names = ['get']
    permission_classes = [AllowAny]

    def get(self, request):
        return Response({'status': 'ok'}, status=status.HTTP_200_OK)


class TermsOfServiceViewSet(BaseViewSet):
    permission_classes = [AllowAny]
    serializer_class = TermsOfServiceSerializer
    queryset = TermsOfService.objects.all()
