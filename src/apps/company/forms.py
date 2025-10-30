from django import forms

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

    class Media:
        js = (
            "js/admin_company_masks.js",
        )
