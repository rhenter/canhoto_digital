from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.company.models import Company
from apps.core.constants import UF_CHOICES
from apps.core.models import AddressFieldsMixin, BaseModel


class Invoice(BaseModel):
    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        verbose_name=_("Company"),
        related_name="invoices"
    )
    number = models.CharField(max_length=60, verbose_name=_("Number"))
    series = models.CharField(max_length=10, blank=True, default="", verbose_name=_("Series"), )
    key = models.CharField(max_length=50, verbose_name=_("Key"))
    issuer_name = models.CharField(max_length=500, verbose_name=_("Issuer Name"))
    issue_date = models.DateField(null=True, blank=True, verbose_name=_("Issue date"))
    recipient_name = models.CharField(max_length=500, verbose_name=_("Recipient Name"))
    recipient_address_street = models.CharField(max_length=255, blank=True, default="", verbose_name=_("Street"))
    recipient_address_number = models.CharField(max_length=255, blank=True, default="", verbose_name=_("Number"))
    recipient_address_neighborhood = models.CharField(max_length=255, blank=True, default="",
                                                      verbose_name=_("Neighborhood"))
    recipient_address_city = models.CharField(max_length=255, blank=True, default="", verbose_name=_("City"))
    recipient_address_uf = models.CharField(
        max_length=2,
        choices=UF_CHOICES,
        blank=True,
        default="",
        verbose_name=_("State (UF)"),
    )
    recipient_address_zip_code = models.CharField(max_length=12, blank=True, default="", verbose_name=_("Zip Code"))
    total_value = models.DecimalField(max_digits=15, decimal_places=2, default=0, verbose_name=_("Total value"), )
    xml_file = models.FileField(upload_to="invoices/xml/", blank=True, null=True, verbose_name=_("XML file"), )
    pdf_file = models.FileField(upload_to="invoices/pdf/", blank=True, null=True, verbose_name=_("DANFE"), )
    status = models.CharField(max_length=30, default="registered", verbose_name=_("Status"))

    class Meta:
        verbose_name = _("Invoice")
        verbose_name_plural = _("Invoices")
        unique_together = ("company", "number", "series")
        ordering = ["-issue_date", "-created_at"]

    def __str__(self):
        return f"NF {self.number}/{self.series} - {str(self.company)} "
