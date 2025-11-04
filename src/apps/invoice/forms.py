from datetime import date, timedelta

from django import forms
from django.utils.translation import gettext_lazy as _

from apps.company.models import Company


class SefazImportForm(forms.Form):
    company = forms.ModelChoiceField(queryset=Company.objects.all(), label=_("Company"))
    start = forms.DateField(initial=date.today() - timedelta(days=30), label=_("Start date"))
    end = forms.DateField(initial=date.today(), label=_("End date"))


class InvoiceXMLImportForm(forms.Form):
    company = forms.ModelChoiceField(queryset=Company.objects.all(), label=_("Company"))
    xml_file = forms.FileField(label=_("NF-e XML file"))
