from datetime import date, timedelta

from django import forms
from django.contrib import admin, messages
from django.shortcuts import redirect, render
from django.urls import path

from apps.company.models import Company
from .models import Invoice
from .tasks import import_from_sefaz


class SefazImportForm(forms.Form):
    company = forms.ModelChoiceField(queryset=Company.objects.all())
    start = forms.DateField(initial=date.today() - timedelta(days=7))
    end = forms.DateField(initial=date.today())


@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = ("id", "company", "number", "series", "issue_date", "total_value", "status", "created_at")
    list_filter = ("company", "status", "issue_date", "created_at")
    search_fields = ("number", "series", "company__name")

    def get_urls(self):
        urls = super().get_urls()
        custom = [
            path("import-sefaz/", self.admin_site.admin_view(self.import_sefaz), name="invoice_import_sefaz"),
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
