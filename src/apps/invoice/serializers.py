from rest_framework import serializers
from .models import Invoice

class InvoiceSerializer(serializers.ModelSerializer):
    company_name = serializers.CharField(source="company.name", read_only=True)
    class Meta:
        model = Invoice
        fields = [
            "id",
            "company",
            "company_name",
            "number",
            "series",
            "issuer_name",
            "issue_date",
            "total_value",
            "recipient_name",
            "recipient_address_street",
            "recipient_address_number",
            "recipient_address_neighborhood",
            "recipient_address_city",
            "recipient_address_uf",
            "recipient_address_zip_code",
            "xml_file",
            "pdf_file",
            "status",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]
