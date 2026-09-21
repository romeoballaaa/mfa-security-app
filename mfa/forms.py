from django import forms

from mfa.services.totp import TOTP_DIGITS, normalize_code


class TOTPCodeForm(forms.Form):
    code = forms.CharField(
        label="Kodi 6-shifror",
        max_length=10,
        widget=forms.TextInput(
            attrs={
                "class": "form-control form-control-lg text-center",
                "inputmode": "numeric",
                "autocomplete": "one-time-code",
                "autofocus": True,
                "placeholder": "000000",
            }
        ),
    )

    def clean_code(self):
        code = normalize_code(self.cleaned_data["code"])
        if len(code) != TOTP_DIGITS or not code.isdigit():
            raise forms.ValidationError("Kodi duhet të ketë 6 shifra.")
        return code