from rest_framework import serializers

from ..constants import BASE_GROUPS
from ..models import User


class UserDetailSerializer(serializers.ModelSerializer):
    name = serializers.CharField(source='get_full_name')

    class Meta:
        model = User
        fields = [
            'id',
            'username',
            'name',
            'cellphone',
            'email',
            'date_joined',
            'allow_email_notifications',
            'allow_push_notifications',
            'allow_sms_notifications',
            'allow_whatsapp_notifications',
            'preferred_language',
            'is_superuser',
            'is_active',
            'last_login',
        ]
        read_only_fields = (
            'id',
            'is_superuser',
            'is_active',
        )


class UserPreferenceSerializer(serializers.ModelSerializer):
    name = serializers.CharField(source='get_full_name', required=False)

    class Meta:
        model = User
        fields = [
            'id',
            'name',
            'allow_email_notifications',
            'allow_push_notifications',
            'allow_sms_notifications',
            'allow_whatsapp_notifications',
            'preferred_language',
        ]
        read_only_fields = (
            'id',
            'name',
        )

    def update(self, instance, validated_data):
        instance = super(UserPreferenceSerializer, self).update(instance, validated_data)
        # Update Groups
        for to_clear in instance.groups.exclude(name__in=BASE_GROUPS):
            instance.groups.remove(to_clear)
        instance.save()
        return instance
