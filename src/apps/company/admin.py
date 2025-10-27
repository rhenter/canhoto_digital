from django.contrib import admin
from django.utils.translation import gettext_lazy as _

from .models import Company


@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "legal_name", "cnpj", "created_at")
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
                "inscricao_estadual", "uf"
            ),
        }),
        ('SEFAZ CONFIG', {
            'fields': (
                'sefaz_environment', 'enable_sefaz_sync',
                'certificate', 'certificate_password', 'certificate_serial',
                'certificate_expires_at'
            ),
            'classes': ['collapse in', ]
        }),
        ('DF-e DISTRIBUTION TRACKING', {
            'fields': (
                'last_nsu', 'last_nsu_updated_at',
                'csc_id', 'csc_token',
            ),
            'classes': ['collapse in', ]
        }),

    )
    readonly_fields = [
        "created_at",
    ]
