from .base import (
    UserBaseSerializer, UserCreateUpdateSerializer, UserProfileSerializer
)  # noqa
from .details import UserDetailSerializer, UserPreferenceSerializer  # noqa

__all__ = [
    'UserBaseSerializer', 'UserProfileSerializer', 'UserCreateUpdateSerializer',
    'UserDetailSerializer', 'UserPreferenceSerializer',
]
