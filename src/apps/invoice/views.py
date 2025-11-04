from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework.response import Response
from django.shortcuts import get_object_or_404

from .models import Invoice
from .serializers import InvoiceSerializer
from .services.import_invoice import import_invoice_from_xml
from apps.company.models import Company

class InvoiceViewSet(viewsets.ModelViewSet):
    queryset = Invoice.objects.select_related("company").all()
    serializer_class = InvoiceSerializer
    permission_classes = [IsAuthenticated]
    filterset_fields = {"company": ["exact"], "number": ["exact", "icontains"], "issue_date": ["gte", "lte"]}
    search_fields = ["number", "series", "company__name"]
    ordering_fields = ["issue_date", "total_value", "created_at"]

    def get_permissions(self):
        if self.action in ["create", "update", "partial_update", "destroy", "import_xml"]:
            return [IsAdminUser()]
        return super().get_permissions()

    @action(detail=False, methods=["post"], url_path="import-xml")
    def import_xml(self, request):
        company_id = request.data.get("company") or request.data.get("company_id")
        xml_file = request.FILES.get("xml_file")
        if not company_id or not xml_file:
            return Response({
                "detail": "company (or company_id) and xml_file are required."
            }, status=status.HTTP_400_BAD_REQUEST)
        company = get_object_or_404(Company, pk=company_id)
        xml_bytes = xml_file.read()
        try:
            invoice, created = import_invoice_from_xml(company, xml_bytes, filename=getattr(xml_file, "name", None))
        except ValueError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        data = InvoiceSerializer(invoice, context={"request": request}).data
        return Response({"invoice": data, "created": created}, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)
