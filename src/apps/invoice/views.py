from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from .models import Invoice
from .serializers import InvoiceSerializer

class InvoiceViewSet(viewsets.ModelViewSet):
    queryset = Invoice.objects.select_related("company").all()
    serializer_class = InvoiceSerializer
    permission_classes = [IsAuthenticated]
    filterset_fields = {"company": ["exact"], "number": ["exact", "icontains"], "issue_date": ["gte", "lte"]}
    search_fields = ["number", "series", "company__name"]
    ordering_fields = ["issue_date", "total_value", "created_at"]

    def get_permissions(self):
        if self.action in ["create", "update", "partial_update", "destroy"]:
            return [IsAdminUser()]
        return super().get_permissions()
