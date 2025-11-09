from rest_framework import serializers
from .models import Company
import re


def _only_digits(value: str | None) -> str:
    return re.sub(r"\D+", "", value or "")


def _mask_cnpj(value: str | None) -> str | None:
    if not value:
        return value
    d = _only_digits(value)[:14]
    if len(d) < 14:
        # partial safety
        return d
    return f"{d[0:2]}.{d[2:5]}.{d[5:8]}/{d[8:12]}-{d[12:14]}"


def _mask_ie_generic(value: str | None) -> str | None:
    if not value:
        return value
    d = _only_digits(value)[:14]
    # generic grouping by 3 with dots
    return re.sub(r"\B(?=(\d{3})+(?!\d))", ".", d)


def _mask_ie_sp(value: str | None) -> str | None:
    if not value:
        return value
    v = (value or "").strip()
    if v.upper() == "ISENTO":
        return "ISENTO"
    # SP has two common formats: 12 digits; or 'P' + 12 digits (produtor rural)
    has_p = v[:1].upper() == "P"
    digits = _only_digits(v[1:] if has_p else v)[:12]
    if len(digits) == 12:
        base = f"{digits[0:3]}.{digits[3:6]}.{digits[6:9]}.{digits[9:12]}"
    else:
        base = re.sub(r"\B(?=(\d{3})+(?!\d))", ".", digits)
    return f"P.{base}" if has_p else base


def _mask_ie_by_uf(value: str | None, uf: str | None) -> str | None:
    if not value:
        return value
    if (value or "").strip().upper() == "ISENTO":
        return "ISENTO"
    u = (uf or "").upper()
    if u == "SP":
        return _mask_ie_sp(value)
    # TODO: extend with more UF-specific masks as needed
    return _mask_ie_generic(value)


class CompanySerializer(serializers.ModelSerializer):
    class Meta:
        model = Company
        fields = [
            "id",
            "name",
            "legal_name",
            "cnpj",
            "inscricao_estadual",
            "address_uf",
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
            "address_street",
            "address_number",
            "address_complement",
            "address_neighborhood",
            "address_city",
            "address_uf",
            "address_zip_code",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at", "certificate_serial", "certificate_expires_at", "last_nsu", "last_nsu_updated_at"]
        extra_kwargs = {
            "certificate_password": {"write_only": True},
            "csc_token": {"write_only": True},
        }

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data["cnpj"] = _mask_cnpj(data.get("cnpj"))
        data["inscricao_estadual"] = _mask_ie_by_uf(data.get("inscricao_estadual"), data.get("address_uf"))
        return data
