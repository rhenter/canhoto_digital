from django.contrib import admin
from .models import Delivery, ProofOfDelivery

@admin.register(Delivery)
class DeliveryAdmin(admin.ModelAdmin):
    list_display = ("id", "code", "status", "assigned_to", "created_at")
    search_fields = ("code", "recipient_expected", "address")
    list_filter = ("status", "created_at")

@admin.register(ProofOfDelivery)
class ProofOfDeliveryAdmin(admin.ModelAdmin):
    list_display = ("id", "delivery", "received_by_name", "signed_at_server")
    search_fields = ("delivery__code", "received_by_name")
    list_filter = ("signed_at_server",)
