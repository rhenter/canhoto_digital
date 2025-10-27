from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.core.models import BaseModel
from .constants import UF_CHOICES, SEFAZ_ENV_CHOICES


class Company(BaseModel):
    # Basic identification
    name = models.CharField(
        max_length=500,
        verbose_name=_("Trade name"),
        help_text=_("Public/commercial trade name"),
    )
    legal_name = models.CharField(
        max_length=500,
        verbose_name=_("Legal name"),
        help_text=_("Registered legal name"),
    )
    cnpj = models.CharField(
        max_length=32,
        unique=True,
        verbose_name=_("CNPJ"),
    )

    # Tax registration
    inscricao_estadual = models.CharField(
        max_length=32,
        blank=True,
        null=True,
        verbose_name=_("State registration (IE)"),
    )

    uf = models.CharField(
        max_length=2,
        choices=UF_CHOICES,
        blank=True,
        null=True,
        verbose_name=_("State (UF)"),
    )

    # SEFAZ environment/config    
    sefaz_environment = models.CharField(
        max_length=16,
        choices=SEFAZ_ENV_CHOICES,
        default="production",
        verbose_name=_("SEFAZ environment"),
    )
    enable_sefaz_sync = models.BooleanField(
        default=True,
        verbose_name=_("Enable SEFAZ sync"),
    )

    # Digital certificate (e-CNPJ)
    certificate = models.FileField(
        upload_to="certificates/",
        blank=True,
        null=True,
        verbose_name=_("Digital certificate (A1)"),
        help_text=_("e-CNPJ (A1) certificate file (.pfx/.p12)"),
    )
    certificate_password = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        verbose_name=_("Certificate password"),
        help_text=_("Password for the digital certificate file"),
    )
    certificate_serial = models.CharField(
        max_length=128,
        blank=True,
        null=True,
        verbose_name=_("Certificate serial number"),
    )
    certificate_expires_at = models.DateTimeField(
        blank=True,
        null=True,
        verbose_name=_("Certificate expiration"),
    )

    # DF-e distribution tracking
    last_nsu = models.BigIntegerField(
        default=0,
        verbose_name=_("Last NSU"),
        help_text=_("Last processed NSU for DF-e distribution"),
    )
    last_nsu_updated_at = models.DateTimeField(
        blank=True,
        null=True,
        verbose_name=_("Last NSU updated at"),
    )

    # NFC-e (optional)
    csc_id = models.CharField(
        max_length=16,
        blank=True,
        null=True,
        verbose_name=_("CSC ID"),
        help_text=_("NFC-e only (Taxpayer Security Code ID)"),
    )
    csc_token = models.CharField(
        max_length=128,
        blank=True,
        null=True,
        verbose_name=_("CSC token"),
        help_text=_("NFC-e only (Taxpayer Security Code token)"),
    )
    is_active = models.BooleanField(default=True, verbose_name=_('Is Active'))

    class Meta:
        verbose_name = _("Company")
        verbose_name_plural = _("Companies")
        ordering = ['name']

    def __str__(self):
        return f"{self.name} ({self.cnpj})"
