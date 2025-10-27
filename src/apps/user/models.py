from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils.translation import gettext_lazy as _
from django_models.models import SignalsModel
from django_models.utils import remove_special_characters

from apps.core.constants import DEFAULT_LANGUAGE_LIST
from apps.core.models import BaseModel
from .managers import UserSignalsManager


class User(SignalsModel, AbstractUser):
    cellphone = models.CharField(max_length=20, blank=True)

    # Notifications
    allow_email_notifications = models.BooleanField(default=True, verbose_name=_("Allow Email Notifications"))
    allow_push_notifications = models.BooleanField(default=True, verbose_name=_("Allow Push Notifications"))
    allow_sms_notifications = models.BooleanField(default=True, verbose_name=_("Allow SMS Notifications"))
    allow_whatsapp_notifications = models.BooleanField(default=True, verbose_name=_("Allow WhatsApp Notifications"))

    preferred_language = models.CharField(
        max_length=10,
        blank=True,
        default='en',
        choices=DEFAULT_LANGUAGE_LIST,
        verbose_name=_('Preferred Language')
    )

    onesignal_id = models.UUIDField(blank=True, null=True)
    objects = UserSignalsManager()

    class Meta:
        verbose_name = _("User")
        verbose_name_plural = _("Users")

    def __str__(self):
        return f'{self.get_full_name()}'

    def _clean_phone(self, value):
        number = remove_special_characters(value.replace(' ', ''))

        if number.startswith('0'):
            number = number[1:]
        return number

    def _register_with_onesignal(self):
        """Register this user with OneSignal for push notifications"""
        from .utils import register_user_with_onesignal
        result = register_user_with_onesignal(self)
        # Return the raw result for backward compatibility
        return result['result'] if result['success'] else None

    def pre_save(self, save_kwargs):
        self.cellphone = self._clean_phone(self.cellphone)
