from rest_framework import serializers
from django.contrib.gis.geos import Point, GEOSGeometry

from apps.invoice.serializers import InvoiceSerializer
from .models import Delivery, ProofOfDelivery, ProofOfDeliveryPhoto


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


class ProofOfDeliveryPhotoSerializer(serializers.ModelSerializer):
    url = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = ProofOfDeliveryPhoto
        fields = ["id", "image", "url", "meta", "created_at"]
        read_only_fields = ["id", "url", "created_at"]

    def get_url(self, obj):
        try:
            return obj.image.url if obj.image else None
        except Exception:
            return None


class PointJSONField(serializers.Field):
    def to_representation(self, value):
        if not value:
            return None
        try:
            # value is a GEOS Point: x=lng, y=lat
            return {"type": "Point", "coordinates": [value.x, value.y]}
        except Exception:
            return None

    def to_internal_value(self, data):
        if data in (None, "", {}):
            return None
        # Accept GeoJSON object or simple [lng, lat] array or WKT string
        try:
            if isinstance(data, (list, tuple)) and len(data) == 2:
                lng, lat = float(data[0]), float(data[1])
                return Point(lng, lat, srid=4326)
            if isinstance(data, dict):
                coords = data.get("coordinates")
                if data.get("type") == "Point" and isinstance(coords, (list, tuple)) and len(coords) == 2:
                    lng, lat = float(coords[0]), float(coords[1])
                    return Point(lng, lat, srid=4326)
            if isinstance(data, str):
                # Try GEOSGeometry from WKT or GeoJSON string
                geom = GEOSGeometry(data, srid=4326)
                if geom.geom_type == "Point":
                    return geom
        except Exception:
            pass
        raise serializers.ValidationError("Invalid location. Use GeoJSON Point or [lng, lat].")


class ProofOfDeliverySerializer(serializers.ModelSerializer):
    photos = ProofOfDeliveryPhotoSerializer(many=True, read_only=True)
    location = PointJSONField(required=False, allow_null=True)

    class Meta:
        model = ProofOfDelivery
        fields = [
            "id",
            "delivery",
            "received_by_name",
            "received_by_document",
            "signed_at",
            "signed_at_server",
            "location",
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
