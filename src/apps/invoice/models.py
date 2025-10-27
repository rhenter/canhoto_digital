from django.db import models
from apps.core.models import BaseModel
from apps.company.models import Company

class Invoice(BaseModel):
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name="invoices")
    number = models.CharField(max_length=60)
    series = models.CharField(max_length=10, blank=True, default="")
    issue_date = models.DateField(null=True, blank=True)
    total_value = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    xml_file = models.FileField(upload_to="invoices/xml/", blank=True, null=True)
    pdf_file = models.FileField(upload_to="invoices/pdf/", blank=True, null=True)
    status = models.CharField(max_length=30, default="registered")

    class Meta:
        unique_together = ("company", "number", "series")
        ordering = ["-issue_date", "-created_at"]

    def __str__(self):
        return f"{self.company.name} - NF {self.number}/{self.series}"
