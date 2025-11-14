from django.contrib.auth import password_validation
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from ..models import User


class ChangePasswordSerializer(serializers.Serializer):
    current_password = serializers.CharField(write_only=True, required=True)
    new_password = serializers.CharField(write_only=True, required=True)

    def validate(self, attrs):
        user: User = self.context.get('user') or self.context.get('request').user
        if not user or not user.is_authenticated:
            raise serializers.ValidationError({"detail": _("Authentication required.")})

        current_password = attrs.get('current_password')
        new_password = attrs.get('new_password')

        if not user.check_password(current_password):
            raise serializers.ValidationError({"current_password": _("Current password is incorrect.")})

        # Validate the new password with Django validators
        try:
            password_validation.validate_password(new_password, user=user)
        except Exception as exc:
            raise serializers.ValidationError({"new_password": list(exc.messages) if hasattr(exc, 'messages') else [str(exc)]})

        if current_password == new_password:
            raise serializers.ValidationError({"new_password": _("New password must be different from the current password.")})

        attrs['user'] = user
        return attrs

    def save(self, **kwargs):
        user: User = self.validated_data['user']
        new_password = self.validated_data['new_password']
        user.set_password(new_password)
        user.save(update_fields=["password"]) 
        return user
