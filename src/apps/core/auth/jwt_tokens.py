from typing import Dict

import jwt
from django.utils import timezone
from rest_framework.authtoken.models import Token
from rest_framework.exceptions import ValidationError

from apps.user.models import User
from apps.user.serializers import UserProfileSerializer


class JwtAuthSession:

    def __init__(self, request_data: Dict) -> None:
        self._request_data = request_data
        self.validated_data = self._get_validated_data(request_data)

    def _get_field_data(self, data: Dict, field: str) -> str:
        field_data = data.get(field, '').strip().replace(' ', '')
        if not field_data:
            raise ValidationError({field: 'This field is required.'})
        return field_data

    def _get_validated_data(self, data: Dict) -> Dict:
        validated_data = {
            'username': self._get_field_data(data, 'username')
        }

        try:
            token_data = jwt.decode(self._get_field_data(data, 'token'), options={"verify_signature": False})
        except jwt.exceptions.DecodeError:
            raise ValidationError({'token': 'Invalid Token'})

        if validated_data['username'] != token_data.get('unique_name', ''):
            raise ValidationError({'token': 'Invalid Token'})

        validated_data.update({
            'first_name': token_data.get('given_name', ''),
            'last_name': token_data.get('family_name', ''),
            'email': token_data.get('unique_name', ''),
        })

        return validated_data

    def set_session(self) -> Dict:
        try:
            user = User.objects.get(username__iexact=self.validated_data.get('username'))
        except User.DoesNotExist:
            user = User.objects.create(**self.validated_data)

        user.last_login = timezone.now()
        user.save()

        token, _ = Token.objects.get_or_create(user=user)
        data = {
            'token': token.key,
            'user': UserProfileSerializer(user).data,
        }
        return data
