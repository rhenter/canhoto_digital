from django import forms
from django.contrib.auth import password_validation
from django.utils.translation import gettext_lazy as _


class ChangePasswordForm(forms.Form):
    password = forms.CharField(
        label=_("New password"), widget=forms.PasswordInput()
    )
    password2 = forms.CharField(
        label=_("New password (verify)"), widget=forms.PasswordInput()
    )
    user = forms.HiddenInput()

    def clean_password(self):
        password = self.cleaned_data['password']
        user = self.cleaned_data.get('user')
        password_validation.validate_password(password, user)
        return password

    def clean_password2(self):
        password = self.cleaned_data.get('password')
        password2 = self.cleaned_data.get('password2')
        fail_conditions = (
            password and password2,
            password != password2
        )
        if all(fail_conditions):
            raise forms.ValidationError(
                _("The two password fields didn't match."),
                code='password_mismatch'
            )
        return password


class ImportForm(forms.Form):
    json_file = forms.FileField()
