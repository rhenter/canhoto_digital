from django import forms
from django.conf import settings
from django.utils.translation import gettext_lazy as _

from .models import Company


class CompanyAdminForm(forms.ModelForm):
    class Meta:
        model = Company
        fields = "__all__"
        widgets = {
            "cnpj": forms.TextInput(attrs={
                "placeholder": "00.000.000/0000-00",
                "inputmode": "numeric",
                "autocomplete": "off",
            }),
            "inscricao_estadual": forms.TextInput(attrs={
                "placeholder": "Inscrição Estadual",
                "inputmode": "numeric",
                "autocomplete": "off",
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # User-facing help must be i18n, code/comments in English.
        self.fields["last_nsu"].help_text = _(
            "Last processed NSU for DF-e distribution. Avoid resetting to 0 unless strictly necessary. "
            "If you reset it, you must wait at least %(minutes)d minutes before attempting any new DF-e requests to avoid SEFAZ cStat=656 (Improper Consumption)."
        ) % {"minutes": settings.SEFAZ_COOLDOWN_MINUTES}
        self.fields["last_nsu_updated_at"].help_text = _(
            "Timestamp of the last NSU update/reset used to evaluate the SEFAZ cooldown window."
        )

    class Media:
        js = (
            "js/admin_company_masks.js",
        )
