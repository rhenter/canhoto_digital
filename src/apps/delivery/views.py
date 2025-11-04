import os, time
import boto3
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from .models import Delivery, ProofOfDelivery
from .serializers import DeliverySerializer, ProofOfDeliverySerializer

class DeliveryViewSet(viewsets.ModelViewSet):
    queryset = Delivery.objects.all().order_by("-created_at")
    serializer_class = DeliverySerializer
    permission_classes = [IsAuthenticated]
    filterset_fields = ["status"]
    search_fields = ["code", "address", "recipient_expected"]
    ordering_fields = ["created_at", "code", "status"]

    def get_queryset(self):
        qs = super().get_queryset()
        if self.request.user.is_superuser:
            return qs
        return qs.filter(assigned_to=self.request.user)

    def get_permissions(self):
        if self.action in ["create", "update", "partial_update", "destroy"]:
            return [IsAdminUser()]
        return super().get_permissions()

    @action(detail=True, methods=["post"])
    def presign(self, request, pk=None):
        delivery = self.get_object()
        files = request.data.get("files", ["signature.png"])
        bucket = os.getenv("AWS_S3_BUCKET_NAME", "")
        region = os.getenv("AWS_S3_REGION_NAME", "us-east-1")
        uploads = []
        if bucket:
            s3 = boto3.client("s3", region_name=region)
            for name in files:
                key = f"deliveries/{delivery.id}/{int(time.time())}/{name}"
                presigned = s3.generate_presigned_post(
                    Bucket=bucket,
                    Key=key,
                    ExpiresIn=60,
                    Fields={},
                    Conditions=[],
                )
                uploads.append({"filename": name, **presigned})
        else:
            for name in files:
                key = f"deliveries/{delivery.id}/{int(time.time())}/{name}"
                url = f"/media/{key}"
                uploads.append({"filename": name, "url": url, "fields": {"key": key}})
        return Response({"uploads": uploads})

    @action(detail=True, methods=["post"])
    def pod(self, request, pk=None):
        delivery = self.get_object()
        serializer = ProofOfDeliverySerializer(data={**request.data, "delivery": delivery.id})
        serializer.is_valid(raise_exception=True)
        pod = serializer.save()
        delivery.status = "delivered"
        delivery.save(update_fields=["status"])
        return Response(ProofOfDeliverySerializer(pod).data, status=status.HTTP_201_CREATED)

class ProofOfDeliveryViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = ProofOfDelivery.objects.select_related("delivery").all().order_by("-signed_at_server")
    serializer_class = ProofOfDeliverySerializer
    permission_classes = [IsAuthenticated]
    filterset_fields = {"signed_at_server": ["gte", "lte"]}
    search_fields = ["delivery__code", "received_by_name"]
    ordering_fields = ["signed_at_server", "created_at"]
