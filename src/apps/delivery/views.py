from django.utils.translation import gettext_lazy as _
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework.response import Response

from apps.core.viewsets import BaseViewSet
from .models import Delivery, ProofOfDelivery, ProofOfDeliveryPhoto
from .serializers import DeliverySerializer, ProofOfDeliverySerializer, ProofOfDeliveryCreateSerializer


class DeliveryViewSet(BaseViewSet):
    queryset = Delivery.objects.all().order_by("-created_at")
    serializer_class = DeliverySerializer
    permission_classes = [IsAuthenticated]
    filterset_fields = ["status"]
    search_fields = ["code", "address", "recipient_expected"]
    ordering_fields = ["created_at", "code", "status"]

    def get_queryset(self):
        qs = super().get_queryset()
        if self.request.user.is_anonymous:
            return qs.none()
        if self.request.user.is_superuser:
            return qs
        return qs.filter(assigned_to=self.request.user)

    def get_permissions(self):
        if self.action in ["create", "update", "partial_update", "destroy"]:
            return [IsAdminUser()]
        return super().get_permissions()

    # @action(detail=True, methods=["post"])
    # def pod(self, request, pk=None):
    #     delivery = self.get_object()
    #     # Permission: only assigned user or staff can submit POD
    #     user = request.user
    #     if not (user and (user.is_staff or user.is_superuser or delivery.assigned_to_id == user.id)):
    #         return Response({"detail": "Not allowed for this delivery."}, status=status.HTTP_403_FORBIDDEN)
    #
    #     data = request.data.copy()
    #     data["delivery"] = str(delivery.id)
    #     if "signature" in request.FILES and "signature_image" not in request.FILES and "signature_image" not in data:
    #         # DRF ModelSerializer will read the file from request.FILES
    #         request.FILES["signature_image"] = request.FILES["signature"]
    #
    #     # Create or update existing POD
    #     instance = getattr(delivery, "pod", None)
    #     serializer = ProofOfDeliverySerializer(instance=instance, data=data, partial=bool(instance))
    #     serializer.is_valid(raise_exception=True)
    #     pod = serializer.save()
    #
    #     # Handle multiple photos from several common keys
    #     photos_files = []
    #     for key in ("photos", "photos[]", "images", "images[]"):
    #         photos_files.extend(request.FILES.getlist(key))
    #     if photos_files:
    #         objs = [ProofOfDeliveryPhoto(pod=pod, image=f) for f in photos_files]
    #         ProofOfDeliveryPhoto.objects.bulk_create(objs)
    #
    #     return Response(ProofOfDeliverySerializer(pod).data,
    #                     status=status.HTTP_201_CREATED if instance is None else status.HTTP_200_OK)


class ProofOfDeliveryViewSet(BaseViewSet):
    queryset = ProofOfDelivery.objects.select_related("delivery").all().order_by("-signed_at_server")
    serializer_class = ProofOfDeliverySerializer
    filterset_fields = {"signed_at_server": ["gte", "lte"]}
    search_fields = ["delivery__code", "received_by_name"]
    ordering_fields = ["signed_at_server", "created_at"]

    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update']:
            return ProofOfDeliveryCreateSerializer
        return self.serializer_class

    def create(self, request, *args, **kwargs):
        delivery = Delivery.objects.filter(id=request.data.get("delivery")).first()
        if not delivery:
            raise ValidationError({"delivery_id": _("Delivery not found.")})

        user = request.user
        if not (user and (user.is_staff or user.is_superuser or delivery.assigned_to_id == user.id)):
            return Response({"detail": "Not allowed for this delivery."}, status=status.HTTP_403_FORBIDDEN)

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        instance = serializer.save()

        headers = self.get_success_headers(serializer.data)
        return Response(self.serializer_class(instance).data, status=status.HTTP_201_CREATED, headers=headers)
