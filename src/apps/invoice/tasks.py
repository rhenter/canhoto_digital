import uuid
from datetime import datetime, date

from celery import shared_task
from django.core.files.base import ContentFile

from apps.company.models import Company
from .models import Invoice
from .sefaz import SefazClient
from .utils_pdf import render_basic_pdf


def run_import_from_sefaz(company_id: uuid.UUID, start: date, end: date) -> dict:
    """Run SEFAZ import synchronously and return a summary dict.

    This helper is used by both the Celery task and the Admin sync view/shell.
    """
    company = Company.objects.get(id=company_id)
    client = SefazClient(company)

    created = 0
    updated = 0
    for inv in client.list_invoices(start, end):
        obj, was_created = Invoice.objects.update_or_create(
            company=company,
            number=inv.number,
            series=inv.series,
            defaults={
                "key": getattr(inv, "key", ""),
                "issue_date": inv.issue_date,
                "total_value": inv.total_value,
                "status": "imported",
                "issuer_name": getattr(inv, "issuer_name", ""),
                "recipient_name": getattr(inv, "recipient_name", ""),
                "recipient_address_street": getattr(inv, "recipient_address_street", ""),
                "recipient_address_number": getattr(inv, "recipient_address_number", ""),
                "recipient_address_neighborhood": getattr(inv, "recipient_address_neighborhood", ""),
                "recipient_address_city": getattr(inv, "recipient_address_city", ""),
                "recipient_address_uf": getattr(inv, "recipient_address_uf", ""),
                "recipient_address_zip_code": getattr(inv, "recipient_address_zip_code", ""),
            },
        )
        # Persist XML when available and key is present; avoid overwriting if already saved
        try:
            if getattr(inv, "raw_xml", None) and getattr(inv, "key", ""):
                if not obj.xml_file or not getattr(obj.xml_file, "name", ""):
                    obj.xml_file.save(f"{inv.key}.xml", ContentFile(inv.raw_xml), save=False)
                    obj.save(update_fields=["xml_file", "updated_at"])
        except Exception:
            # Do not fail the whole import due to file storage issues
            pass
        # Generate and persist PDF for full documents (procNFe) when possible
        try:
            if getattr(inv, "doc_kind", "") == "procNFe" and getattr(inv, "raw_xml", None):
                if not obj.pdf_file or not getattr(obj.pdf_file, "name", ""):
                    pdf_bytes = render_basic_pdf(inv, inv.raw_xml)
                    if pdf_bytes:
                        obj.pdf_file.save(f"{inv.key}.pdf", ContentFile(pdf_bytes), save=False)
                        obj.save(update_fields=["pdf_file", "updated_at"])
        except Exception:
            pass
        created += int(was_created)
        updated += int(not was_created)
    return {"created": created, "updated": updated}


@shared_task
def import_from_sefaz(company_id: uuid.UUID, start_iso: str, end_iso: str) -> dict:
    """Celery task wrapper that delegates to the synchronous helper."""
    start = datetime.fromisoformat(start_iso).date()
    end = datetime.fromisoformat(end_iso).date()
    return run_import_from_sefaz(company_id, start, end)
