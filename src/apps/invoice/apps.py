from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class InvoiceConfig(AppConfig):
    name = "apps.invoice"
    verbose_name = _("Invoice")
