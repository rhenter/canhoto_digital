from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Tuple, Optional

from django.core.files.base import ContentFile

from apps.company.models import Company
from apps.invoice.models import Invoice
from apps.invoice.integrations.sefaz import parse_nfe_xml


@dataclass(frozen=True)
class ImportResult:
    invoice: Invoice
    created: bool


def _safe_xml_filename(key: Optional[str], fallback_name: Optional[str]) -> str:
    base = (key or fallback_name or "invoice").strip() or "invoice"
    if not base.lower().endswith(".xml"):
        base = f"{base}.xml"
    return base


def import_invoice_from_xml(company: Company, xml_bytes: bytes, *, filename: str | None = None) -> Tuple[Invoice, bool]:
    """
    Create or update an `Invoice` for the given `company` from NF-e XML bytes.

    - Parses the XML (supports `NFe`, `procNFe`, `nfeProc`).
    - Upserts primarily by (company, key) when the NF-e key is present; otherwise fallback to (company, number, series).
    - Saves the given XML into `invoice.xml_file` with a safe filename using the NF key when available.

    Returns: (invoice, created)
    Raises: ValueError (parse errors or missing required fields)
    """
    data = parse_nfe_xml(xml_bytes)

    key = (data.get("key") or "").strip()
    number = data["number"]
    series = data.get("series") or ""

    inv: Invoice | None = None
    created = False

    # Prefer lookup by key, if available
    if key:
        inv = Invoice.objects.filter(company=company, key=key).first()

    if inv is None:
        inv, created = Invoice.objects.get_or_create(
            company=company,
            number=number,
            series=series,
            defaults={
                "key": key,
                "issuer_name": data.get("issuer_name", ""),
                "issue_date": data.get("issue_date"),
                "total_value": data.get("total_value") or Decimal("0"),
                "recipient_name": data.get("recipient_name", ""),
                "recipient_address_street": data.get("recipient_address_street", ""),
                "recipient_address_number": data.get("recipient_address_number", ""),
                "recipient_address_neighborhood": data.get("recipient_address_neighborhood", ""),
                "recipient_address_city": data.get("recipient_address_city", ""),
                "recipient_address_uf": data.get("recipient_address_uf", ""),
                "recipient_address_zip_code": data.get("recipient_address_zip_code", ""),
            },
        )
    else:
        # Update selected fields if found by key
        for field in [
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
        ]:
            setattr(inv, field, data.get(field, getattr(inv, field)))
        # Keep number/series in sync if provided
        inv.number = number or inv.number
        inv.series = series or inv.series
        inv.save()

    # Persist XML file (overwrite with latest content to keep in sync)
    xml_filename = _safe_xml_filename(key, filename)
    inv.xml_file.save(xml_filename, ContentFile(xml_bytes), save=True)

    return inv, created
