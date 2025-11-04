from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from ..models import User

USER_FIELDS = [
    'id',
    'username',
    'first_name',
    'last_name',
    'cellphone',
    'email',
    'allow_email_notifications',
    'allow_push_notifications',
    'allow_sms_notifications',
    'allow_whatsapp_notifications',
    'preferred_language',
    'is_superuser',
    'is_active',
    'last_login',
]


class UserBaseSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = [
            'id',
            'username',
            'first_name',
            'last_name',
            'cellphone',
            'email',
            'is_superuser',
            'is_active',
            'last_login',
        ]


class UserProfileSerializer(UserBaseSerializer):
    name = serializers.CharField(source='get_full_name', required=False)

    class Meta:
        model = User
        fields = ['name'] + USER_FIELDS


class UserCreateUpdateSerializer(UserBaseSerializer):
    class Meta:
        model = User
        fields = USER_FIELDS
        read_only_fields = (
            'id',
            'is_superuser',
            'is_active',
            'last_login',
        )

    def validate_preferred_plant_area(self, value):
        if '-' not in value or value.count('-') > 1:
            raise serializers.ValidationError(_("Invalid plant area format."))
        value = '-'.join([text.strip().lower() for text in value.split('-')])
        return value
