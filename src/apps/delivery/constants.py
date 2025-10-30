from django.utils.translation import gettext_lazy as _

STATUS_CHOICES = [
    ("pending", _("Pending")),
    ("delivered", _("Delivered")),
    ("failed", _("Failed")),
    ("partial", _("Partial")),
]
