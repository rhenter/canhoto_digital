from django.db import models
from django.contrib.auth import get_user_model
from apps.core.models import BaseModel
User = get_user_model()

class Delivery(BaseModel):
    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("delivered", "Delivered"),
        ("failed", "Failed"),
        ("partial", "Partial"),
    ]
    code = models.CharField(max_length=50, unique=True, help_text="External reference: NF/CTe/Order code")
    recipient_expected = models.CharField(max_length=120, blank=True)
    address = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    assigned_to = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, related_name="deliveries")

    def __str__(self):
        return f"{self.code} ({self.status})"

class ProofOfDelivery(BaseModel):
    delivery = models.OneToOneField(Delivery, on_delete=models.CASCADE, related_name="pod")
    received_by_name = models.CharField(max_length=120)
    received_by_document = models.CharField(max_length=40, blank=True)
    signed_at = models.DateTimeField(help_text="Client device timestamp")
    signed_at_server = models.DateTimeField(auto_now_add=True, help_text="Server timestamp (trusted)")
    geo_lat = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    geo_lng = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    signature_image = models.URLField(help_text="URL to signature image (e.g., S3 presigned object)")
    photos = models.JSONField(default=list, help_text="List of URLs to photos (e.g., S3 objects)")
    meta = models.JSONField(default=dict, help_text="Metadata (device_id, app_version, etc.)")

    def __str__(self):
        return f"POD for {self.delivery.code}"
