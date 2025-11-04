from django.contrib import messages
from django.core.files.base import ContentFile
from django.utils.translation import gettext_lazy as _

from .integrations.sefaz import SefazClient, generate_and_save_danfe


def action_fetch_xml_from_sefaz(modeladmin, request, queryset):
    """Bulk action: fetch XML from SEFAZ for selected invoices (by key) and save to xml_file."""
    success = 0
    failed = 0
    skipped = 0
    for inv in queryset:
        key = getattr(inv, "key", "") or ""
        if not key or len(key) < 44:
            skipped += 1
            continue
        try:
            client = SefazClient(inv.company)
            xml_bytes, kind = client.fetch_xml_by_key(key)
            filename = f"{key}.xml"
            # Always overwrite to ensure latest XML
            inv.xml_file.save(filename, ContentFile(xml_bytes), save=True)
            success += 1
        except Exception:
            failed += 1
    if success:
        messages.success(request, _(f"XML downloaded from SEFAZ for {success} invoice(s)."))
    if skipped:
        messages.info(request, _(f"Skipped {skipped} invoice(s) without a valid NF-e key."))
    if failed:
        messages.error(request, _(f"Failed to download XML for {failed} invoice(s). Check credentials, key, and SEFAZ status."))


action_fetch_xml_from_sefaz.short_description = _("Download XML from SEFAZ")


def action_generate_danfe(modeladmin, request, queryset):
    """Bulk action to generate DANFE PDFs for selected invoices using saved XML."""
    success = 0
    skipped = 0
    failed = 0
    for inv in queryset:
        try:
            # If PDF exists, overwrite to reflect current XML
            generated = generate_and_save_danfe(inv, overwrite=True)
            if generated:
                success += 1
            else:
                skipped += 1
        except Exception:  # keep processing others
            failed += 1
    if success:
        messages.success(request, _(f"DANFE generated for {success} invoice(s)."))
    if skipped:
        messages.info(request, _(f"Skipped {skipped} invoice(s) (already had PDF and overwrite disabled)."))
    if failed:
        messages.error(request, _(f"Failed to generate DANFE for {failed} invoice(s). Check XML files and logs."))


action_generate_danfe.short_description = _("Generate DANFE (from XML)")
