from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class DeliveryConfig(AppConfig):
    name = "apps.delivery"
    verbose_name = _("Delivery")
