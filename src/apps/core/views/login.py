from django.utils import timezone
from django_models.utils import remove_special_characters
from rest_framework.authtoken.models import Token
from rest_framework.authtoken.views import ObtainAuthToken
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.auth.jwt_tokens import JwtAuthSession
from apps.user.serializers import UserProfileSerializer
from proj_settings.utils import is_email


class UserLoginDRFTokenView(ObtainAuthToken):
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        data = request.data

        username = data['username'].strip().replace(' ', '')
        if not is_email(username):
            username = remove_special_characters(username)
        data['username'] = username

        serializer = self.serializer_class(data=data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data['user']
        token, created = Token.objects.get_or_create(user=user)
        data = {
            'token': token.key,
            'user': UserProfileSerializer(user).data,
        }
        user.last_login = timezone.now()
        user.save()
        return Response(data)


class UserSetSessionTokenView(APIView):

    def post(self, request, *args, **kwargs):
        authenticator = JwtAuthSession(request.data)
        data = authenticator.set_session()
        return Response(data)
