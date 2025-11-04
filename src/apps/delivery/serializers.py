from rest_framework import serializers

from apps.invoice.serializers import InvoiceSerializer
from .models import Delivery, ProofOfDelivery


class DeliverySerializer(serializers.ModelSerializer):
    invoice = InvoiceSerializer(read_only=True)

    class Meta:
        model = Delivery
        fields = [
            "id",
            "code",
            "status",
            "invoice",
            "observations",
            "assigned_to",
            "created_at",
            "delivery_at"
        ]
        read_only_fields = [
            "id",
            "created_at",
            "delivery_at"
        ]


class ProofOfDeliverySerializer(serializers.ModelSerializer):
    class Meta:
        model = ProofOfDelivery
        fields = [
            "id",
            "delivery",
            "received_by_name",
            "received_by_document",
            "signed_at",
            "signed_at_server",
            "geo_lat",
            "geo_lng",
            "signature_image",
            "photos",
            "meta",
            "created_at",
            "updated_at"
        ]
        read_only_fields = [
            "id",
            "signed_at_server",
            "created_at",
            "updated_at"
        ]
