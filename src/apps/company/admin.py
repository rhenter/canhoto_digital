from django.contrib import admin
from django.urls import reverse
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _

from .forms import CompanyAdminForm
from .models import Company
from ..core.templatetags.app_utils import cnpj_mask


@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
    form = CompanyAdminForm
    list_display = ("code", "name", "legal_name", "_cnpj", "_created_at", "invoices_link", "deliveries_link")
    search_fields = ("name", "legal_name", "cnpj")
    list_filter = ("created_at",)

    fieldsets = (
        ('STATUS', {
            'fields': ('is_active', "created_at")
        }),
        (_('IDENTIFICATION'), {
            'fields': ("name", "legal_name", "cnpj",),
        }),

        (_('TAX REGISTRATION'), {
            'fields': (
                "inscricao_estadual",
            ),
        }),
        (_('ADDRESS'), {
            'fields': (
                "address_street", "address_neighborhood", "address_city", "address_uf"
            ),
        }),
        ('SEFAZ CONFIG', {
            'fields': (
                'sefaz_environment', 'enable_sefaz_sync',
                'certificate', 'certificate_password', 'certificate_serial',
                'certificate_expires_at'
            ),
        }),
        ('DF-e DISTRIBUTION TRACKING', {
            'fields': (
                'last_nsu', 'last_nsu_updated_at',
                'csc_id', 'csc_token',
            ),
        }),

    )
    readonly_fields = [
        "created_at",
    ]

    def _cnpj(self, obj):
        return cnpj_mask(obj.cnpj)

    _cnpj.short_description = 'CNPJ'

    def _created_at(self, obj):
        return obj.created_at.strftime('%Y-%m-%d %H:%M')

    _created_at.short_description = _('Created at')
    _created_at.admin_order_field = 'created_at'

    def invoices_link(self, obj):
        invoices_link = f"{reverse('admin:invoice_invoice_changelist')}?company={obj.id}"
        return format_html(
            "<a href='{url}' style='text-align: center'>{title}</a>",
            url=invoices_link,
            title=_('Invoices')
        )

    invoices_link.allow_tags = True
    invoices_link.short_description = _("Invoices")

    def deliveries_link(self, obj):
        deliveries_link = f"{reverse('admin:delivery_delivery_changelist')}?invoice__company={obj.id}"
        return format_html(
            "<a href='{url}' style='text-align: center'>{title}</a>",
            url=deliveries_link,
            title=_('Deliveries')
        )

    deliveries_link.allow_tags = True
    deliveries_link.short_description = _("Deliveries")
