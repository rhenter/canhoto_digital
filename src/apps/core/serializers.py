from typing import Any

from django.contrib.auth.models import update_last_login
from rest_framework import serializers
from rest_framework.serializers import raise_errors_on_nested_writes
from rest_framework.utils import model_meta
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer, TokenObtainSerializer
from rest_framework_simplejwt.settings import api_settings
from rest_framework_simplejwt.tokens import RefreshToken

from .models import TermsOfService
from ..user.serializers import UserProfileSerializer


class TermsOfServiceSerializer(serializers.ModelSerializer):
    class Meta:
        model = TermsOfService
        fields = [
            'id',
            'profile_type',
            'text',
        ]
        read_only_fields = (
            'id',
        )


class ToggleSerializer(serializers.Serializer):
    value = serializers.BooleanField()


class AuditChangesSerializer(serializers.ModelSerializer):
    fields_changed = []

    def update(self, instance, validated_data):
        raise_errors_on_nested_writes('update', self, validated_data)
        info = model_meta.get_field_info(instance)

        # Simply set each attribute on the instance, and then save it.
        # Note that unlike `.create()` we don't need to treat many-to-many
        # relationships as being a special case. During updates we already
        # have an instance pk for the relationships to be associated with.
        m2m_fields = []
        for attr, value in validated_data.items():
            if attr in info.relations and info.relations[attr].to_many:
                m2m_fields.append((attr, value))
            else:
                if getattr(instance, attr) != value:
                    self.fields_changed.append(attr)
                setattr(instance, attr, value)

        instance.save()

        # Note that many-to-many fields are set after updating instance.
        # Setting m2m fields triggers signals which could potentially change
        # updated instance and we do not want it to collide with .update()
        for attr, value in m2m_fields:
            if getattr(instance, attr) != value:
                self.fields_changed.append(attr)
            field = getattr(instance, attr)
            field.set(value)

        return instance
