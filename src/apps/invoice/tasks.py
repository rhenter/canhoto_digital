from datetime import datetime

from celery import shared_task

from apps.company.models import Company
from .models import Invoice
from .sefaz import SefazClient


@shared_task
def import_from_sefaz(company_id: int, start_iso: str, end_iso: str) -> dict:
    company = Company.objects.get(id=company_id)
    client = SefazClient(company)
    start = datetime.fromisoformat(start_iso).date()
    end = datetime.fromisoformat(end_iso).date()

    created = 0
    updated = 0
    for inv in client.list_invoices(start, end):
        obj, was_created = Invoice.objects.update_or_create(
            company=company,
            number=inv.number,
            series=inv.series,
            defaults={
                "issue_date": inv.issue_date,
                "total_value": inv.total_value,
                "status": "imported",
            },
        )
        created += int(was_created)
        updated += int(not was_created)
    return {"created": created, "updated": updated}
