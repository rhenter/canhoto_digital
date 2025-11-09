from datetime import timedelta

from django.conf import settings
from django.contrib import admin, messages
from django.urls import reverse
from django.utils import timezone
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _

from apps.core.templatetags.app_utils import cnpj_mask
from .forms import CompanyAdminForm
from .models import Company


@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
    form = CompanyAdminForm
    list_display = (
        "code",
        "name",
        "_cnpj",
        "cooldown_status",
        "_created_at",
        "invoices_link",
        "deliveries_link"
    )
    search_fields = ("name", "legal_name", "cnpj")
    list_filter = ("created_at",)
    actions = ["action_safe_nsu_reset"]

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
                "address_street",
                "address_number",
                "address_complement",
                "address_neighborhood",
                "address_city",
                "address_uf",
                "address_zip_code",
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

    def cooldown_status(self, obj):
        # Display a simple status indicating whether the company is within the SEFAZ cooldown window
        now = timezone.now()
        if obj.last_nsu_updated_at and (now - obj.last_nsu_updated_at) < timedelta(minutes=settings.SEFAZ_COOLDOWN_MINUTES):
            minutes_left = settings.SEFAZ_COOLDOWN_MINUTES - int((now - obj.last_nsu_updated_at).total_seconds() // 60)
            return format_html(
                "<span style='color:#b45309;font-weight:600' title='{title}'>⚠ {text}</span>",
                title=_('Within SEFAZ cooldown window'),
                text=_('Cooldown: ~%(minutes)d min left') % {"minutes": max(0, minutes_left)},
            )
        return format_html(
            "<span style='color:#065f46;font-weight:600' title='{title}'>✔ {text}</span>",
            title=_('Outside SEFAZ cooldown window'),
            text=_('Ready'),
        )

    cooldown_status.short_description = _('SEFAZ cooldown')

    # Admin action to safely reset NSU with cooldown validation
    def action_safe_nsu_reset(self, request, queryset):
        now = timezone.now()
        resets = 0
        blocked = 0
        for company in queryset:
            allowed = True
            if company.last_nsu_updated_at:
                if now - company.last_nsu_updated_at < timedelta(minutes=settings.SEFAZ_COOLDOWN_MINUTES):
                    allowed = False
            if not allowed:
                blocked += 1
                messages.warning(
                    request,
                    _("NSU reset blocked for %(company)s: still within SEFAZ cooldown window (%(minutes)d minutes).")
                    % {"company": company.name, "minutes": settings.SEFAZ_COOLDOWN_MINUTES}
                )
                continue
            company.last_nsu = 0
            company.last_nsu_updated_at = now
            company.save(update_fields=["last_nsu", "last_nsu_updated_at", "updated_at"])
            resets += 1
        if resets:
            messages.success(request, _("Safely reset NSU for %(count)d compan(ies).") % {"count": resets})
        if not resets and not blocked:
            messages.info(request, _("No companies selected for NSU reset."))

    action_safe_nsu_reset.short_description = _("Safe NSU reset (respects SEFAZ cooldown)")
