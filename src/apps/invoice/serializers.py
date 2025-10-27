from rest_framework import serializers
from .models import Invoice

class InvoiceSerializer(serializers.ModelSerializer):
    company_name = serializers.CharField(source="company.name", read_only=True)
    class Meta:
        model = Invoice
        fields = ["id", "company", "company_name", "number", "series", "issue_date", "total_value", "xml_file", "pdf_file", "status", "created_at", "updated_at"]
        read_only_fields = ["id", "created_at", "updated_at"]
