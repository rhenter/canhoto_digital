from rest_framework import serializers
from .models import Company

class CompanySerializer(serializers.ModelSerializer):
    class Meta:
        model = Company
        fields = [
            "id",
            "name",
            "legal_name",
            "cnpj",
            "inscricao_estadual",
            "uf",
            "sefaz_environment",
            "enable_sefaz_sync",
            "certificate",
            "certificate_password",
            "certificate_serial",
            "certificate_expires_at",
            "last_nsu",
            "last_nsu_updated_at",
            "csc_id",
            "csc_token",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at", "certificate_serial", "certificate_expires_at", "last_nsu", "last_nsu_updated_at"]
        extra_kwargs = {
            "certificate_password": {"write_only": True},
            "csc_token": {"write_only": True},
        }
