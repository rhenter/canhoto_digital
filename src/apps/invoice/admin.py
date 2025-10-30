from datetime import date, timedelta
import uuid

from django import forms
from django.contrib import admin, messages
from django.core.files.base import ContentFile
from django.shortcuts import redirect, render
from django.urls import path, reverse
from django.utils.translation import gettext_lazy as _
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_protect
from django.shortcuts import get_object_or_404

from apps.company.models import Company
from .models import Invoice
from .tasks import import_from_sefaz
from .sefaz import generate_and_save_danfe
from .sefaz import SefazClient


class SefazImportForm(forms.Form):
    company = forms.ModelChoiceField(queryset=Company.objects.all())
    start = forms.DateField(initial=date.today() - timedelta(days=7))
    end = forms.DateField(initial=date.today())


@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    change_form_template = "admin/invoice/invoice/change_form.html"
    list_display = ("code", "company", "number", "series", "issue_date", "total_value", "status", "created_at")
    list_filter = ("company", "status", "issue_date", "created_at")
    search_fields = ("number", "series", "company__name")
    fieldsets = (
        ("", {
            'fields': ("company", "status"),
        }),
        (_('NF-e DATA'), {
            'fields': (
                "number", "series", "key", "issuer_name", "issue_date", "total_value",
            ),
        }),
        (_('RECIPIENT DATA'), {
            'fields': (
                "recipient_name",
            ),
        }),
        (_('RECIPIENT ADDRESS'), {
            'fields': (
                "recipient_address_street", "recipient_address_number", "recipient_address_neighborhood",
                "recipient_address_city", "recipient_address_uf", "recipient_address_zip_code"
            ),
        }),
        ('FILES', {
            'fields': (
                'xml_file', 'pdf_file',
            ),
        }),
    )
    readonly_fields = [
        "created_at",
    ]
    actions = ["action_fetch_xml_from_sefaz", "action_generate_danfe"]

    def get_urls(self):
        urls = super().get_urls()
        custom = [
            path("import-sefaz/", self.admin_site.admin_view(self.import_sefaz), name="invoice_import_sefaz"),
            path("generate-danfe/<uuid:pk>/", self.admin_site.admin_view(self.generate_danfe_view), name="invoice_invoice_generate_danfe"),
            path("download-xml/<uuid:pk>/", self.admin_site.admin_view(self.download_xml_view), name="invoice_invoice_download_xml"),
        ]
        return custom + urls

    def import_sefaz(self, request):
        if request.method == "POST":
            form = SefazImportForm(request.POST)
            if form.is_valid():
                company = form.cleaned_data["company"]
                start = form.cleaned_data["start"]
                end = form.cleaned_data["end"]
                task = import_from_sefaz.delay(company.id, start.isoformat(), end.isoformat())
                messages.success(request, f"Import task queued: {company.name} ({start}→{end}). Task id: {task.id}")
                return redirect("admin:invoice_invoice_changelist")
        else:
            form = SefazImportForm()
        context = dict(self.admin_site.each_context(request), form=form, title="Import SEFAZ Invoices")
        return render(request, "admin/invoice/invoice/import_form.html", context)

    def action_fetch_xml_from_sefaz(self, request, queryset):
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
            except Exception as e:
                failed += 1
        if success:
            messages.success(request, _(f"XML downloaded from SEFAZ for {success} invoice(s)."))
        if skipped:
            messages.info(request, _(f"Skipped {skipped} invoice(s) without a valid NF-e key."))
        if failed:
            messages.error(request, _(f"Failed to download XML for {failed} invoice(s). Check credentials, key, and SEFAZ status."))

    action_fetch_xml_from_sefaz.short_description = _("Download XML from SEFAZ")

    def action_generate_danfe(self, request, queryset):
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
            except Exception as e:  # keep processing others
                failed += 1
        if success:
            messages.success(request, _(f"DANFE generated for {success} invoice(s)."))
        if skipped:
            messages.info(request, _(f"Skipped {skipped} invoice(s) (already had PDF and overwrite disabled)."))
        if failed:
            messages.error(request, _(f"Failed to generate DANFE for {failed} invoice(s). Check XML files and logs."))

    action_generate_danfe.short_description = _("Generate DANFE (from XML)")

    def generate_danfe_view(self, request, pk: uuid.UUID):
        inv = get_object_or_404(Invoice, pk=pk)
        if not self.has_change_permission(request, obj=inv):
            messages.error(request, _("You do not have permission to generate DANFE for this invoice."))
            return redirect("admin:invoice_invoice_change", object_id=inv.pk)
        try:
            generate_and_save_danfe(inv, overwrite=True)
            messages.success(request, _("DANFE generated and saved successfully."))
        except Exception as e:
            messages.error(request, _(f"Failed to generate DANFE: {e}"))
        return redirect("admin:invoice_invoice_change", object_id=inv.pk)

    def download_xml_view(self, request, pk: uuid.UUID):
        inv = get_object_or_404(Invoice, pk=pk)
        if not self.has_change_permission(request, obj=inv):
            messages.error(request, _("You do not have permission to download XML for this invoice."))
            return redirect("admin:invoice_invoice_change", object_id=inv.pk)
        key = getattr(inv, "key", "") or ""
        if not key or len(key) < 44:
            messages.error(request, _("Invoice has no valid NF-e key (44 chars)."))
            return redirect("admin:invoice_invoice_change", object_id=inv.pk)
        try:
            client = SefazClient(inv.company)
            xml_bytes, kind = client.fetch_xml_by_key(key)
            filename = f"{key}.xml"
            inv.xml_file.save(filename, ContentFile(xml_bytes), save=True)
            if kind != "procNFe":
                messages.warning(request, _("XML saved, but SEFAZ returned a summary (resNFe). Full DANFE may not be possible."))
            else:
                messages.success(request, _("XML downloaded from SEFAZ and saved successfully."))
        except Exception as e:
            messages.error(request, _(f"Failed to download XML from SEFAZ: {e}"))
        return redirect("admin:invoice_invoice_change", object_id=inv.pk)
