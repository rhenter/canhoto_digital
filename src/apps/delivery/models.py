from django.contrib.auth import get_user_model
from django.db import models
from django.utils.translation import gettext_lazy as _
from django.contrib.gis.db import models as gis_models

from apps.core.models import BaseModel
from apps.delivery.constants import STATUS_CHOICES

User = get_user_model()


class Delivery(BaseModel):
    invoice = models.OneToOneField(
        "invoice.Invoice",
        on_delete=models.CASCADE,
        verbose_name=_("Invoice"),
        related_name="deliveries",
    )
    assigned_to = models.ForeignKey(
        User, null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name="deliveries",
        verbose_name=_("Assigned to")
    )
    observations = models.TextField(blank=True, default="", verbose_name=_("Observations"))
    status = models.CharField(max_length=20, blank=True, choices=STATUS_CHOICES, default="pending",
                              verbose_name=_("Status"))
    delivery_at = models.DateTimeField(null=True, blank=True, verbose_name=_('Delivery at'))

    class Meta:
        verbose_name = _("Delivery")
        verbose_name_plural = _("Deliveries")
        ordering = ["-created_at"]

    def __str__(self):
        return f"{str(self.invoice)} ({self.get_status_display()})"


class ProofOfDelivery(BaseModel):
    delivery = models.OneToOneField(
        Delivery,
        on_delete=models.CASCADE,
        related_name="pod",
        verbose_name=_("Delivery")
    )
    received_by_name = models.CharField(max_length=120, verbose_name=_("Received by"))
    received_by_document = models.CharField(max_length=40, blank=True, verbose_name=_("Received by Document"))
    signed_at = models.DateTimeField(help_text="Client device timestamp", verbose_name=_("Signed at"))
    signed_at_server = models.DateTimeField(auto_now_add=True, help_text="Server timestamp (trusted)",
                                            verbose_name=_("Signed at Server"))
    location = gis_models.PointField(srid=4326, geography=True, null=True, blank=True, verbose_name=_("Location"))
    signature_image = models.ImageField(upload_to="delivery/signatures/", blank=True, null=True,
                                      verbose_name=_("Signature Image"))
    meta = models.JSONField(default=dict, help_text="Metadata (device_id, app_version, etc.)", verbose_name=_("Meta"))

    class Meta:
        verbose_name = _("Proof of Delivery")
        verbose_name_plural = _("Proof of Deliveries")
        ordering = ["-created_at"]

    def __str__(self):
        return f"POD for {self.delivery.invoice.number}"


class ProofOfDeliveryPhoto(BaseModel):
    pod = models.ForeignKey(ProofOfDelivery, on_delete=models.CASCADE, related_name="photos", verbose_name=_("POD"))
    image = models.ImageField(upload_to="delivery/photos/", verbose_name=_("Photo"))
    meta = models.JSONField(default=dict, blank=True, verbose_name=_("Meta"))

    class Meta:
        verbose_name = _("POD Photo")
        verbose_name_plural = _("POD Photos")
        ordering = ["-created_at"]
