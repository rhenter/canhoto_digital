from django.db import transaction
from rest_framework import serializers
from django.contrib.gis.geos import Point, GEOSGeometry

from apps.invoice.serializers import InvoiceSerializer
from .models import Delivery, ProofOfDelivery, ProofOfDeliveryPhoto
from ..core.serializers import AuditChangesSerializer


class DeliverySerializer(serializers.ModelSerializer):
    invoice = InvoiceSerializer(read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model = Delivery
        fields = [
            "id",
            "code",
            "status",
            "status_display",
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
        # Accept GeoJSON object, [lng, lat] array, JSON-encoded strings, comma strings, or WKT
        try:
            # 1) Python list/tuple
            if isinstance(data, (list, tuple)) and len(data) == 2:
                lng, lat = float(data[0]), float(data[1])
                return Point(lng, lat, srid=4326)

            # 2) Dict: GeoJSON or lat/lng keys
            if isinstance(data, dict):
                # GeoJSON
                coords = data.get("coordinates")
                if data.get("type") == "Point" and isinstance(coords, (list, tuple)) and len(coords) == 2:
                    lng, lat = float(coords[0]), float(coords[1])
                    return Point(lng, lat, srid=4326)
                # {lng: ..., lat: ...} or {longitude: ..., latitude: ...}
                if {"lng", "lat"}.issubset(data.keys()):
                    return Point(float(data["lng"]), float(data["lat"]), srid=4326)
                if {"longitude", "latitude"}.issubset(data.keys()):
                    return Point(float(data["longitude"]), float(data["latitude"]), srid=4326)

            # 3) Strings
            if isinstance(data, str):
                s = data.strip()
                # JSON-encoded array/dict coming from multipart forms
                if s.startswith("[") or s.startswith("{"):
                    import json
                    try:
                        parsed = json.loads(s)
                        return self.to_internal_value(parsed)
                    except Exception:
                        # fall through to other parsers
                        pass
                # Comma-separated "lng,lat"
                if "," in s:
                    parts = [p.strip() for p in s.split(",")]
                    if len(parts) == 2:
                        lng, lat = float(parts[0]), float(parts[1])
                        return Point(lng, lat, srid=4326)
                # Try WKT/GeoJSON via GEOS
                geom = GEOSGeometry(s, srid=4326)
                if geom.geom_type == "Point":
                    return geom
        except Exception:
            # Normalize any parsing error into a validation error below
            pass
        raise serializers.ValidationError("Invalid location. Use GeoJSON Point, [lng, lat], 'lng,lat' or JSON string.")


class ProofOfDeliverySerializer(serializers.ModelSerializer):
    photos = ProofOfDeliveryPhotoSerializer(many=True, read_only=True)
    location = PointJSONField(required=False, allow_null=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model = ProofOfDelivery
        fields = [
            "id",
            "delivery",
            "received_by_name",
            "status",
            "status_display",
            "observations",
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


class ProofOfDeliveryCreateSerializer(AuditChangesSerializer):
    signature_image = serializers.FileField(required=False)
    location = PointJSONField(required=False, allow_null=True)

    class Meta:
        model = ProofOfDelivery
        fields = [
            "id",
            "delivery",
            "received_by_name",
            "status",
            "observations",
            "received_by_document",
            "signed_at",
            "signed_at_server",
            "location",
            "signature_image",
            "meta",
            "created_at",
            "updated_at"
        ]
        read_only_fields = [
            "id",
            "created_at",
            "updated_at"
        ]

    def create(self, validated_data):
        with transaction.atomic():

            instance = super().create(validated_data)

            # Handle photos coming either as a single file or a list of files
            request = self.context.get('request')
            photos = []
            if request is not None:
                # Prefer FILES to avoid iterating over file chunks
                try:
                    files = request.FILES.getlist('photos') if hasattr(request, 'FILES') else []
                except Exception:
                    files = []
                if not files:
                    single = request.FILES.get('photos') if hasattr(request, 'FILES') else None
                    if single:
                        files = [single]
                # Some clients may send it merged into data
                if not files:
                    data_photos = request.data.get('photos')
                    if data_photos:
                        if isinstance(data_photos, (list, tuple)):
                            files = list(data_photos)
                        else:
                            files = [data_photos]
                photos = files
            else:
                data_photos = validated_data.pop('photos', [])
                if data_photos:
                    photos = list(data_photos) if isinstance(data_photos, (list, tuple)) else [data_photos]

            meta = request.data.get('meta', {}) if request is not None else {}
            for photo in photos:
                if not photo:
                    continue
                instance.photos.create(image=photo, meta=meta)

        return instance