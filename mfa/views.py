from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.cache import never_cache

from audit.models import SecurityEvent
from audit.services import record_event

from .forms import TOTPCodeForm
from .services.totp import (
    build_provisioning_uri,
    build_qr_data_uri,
    confirm_device,
    format_secret_for_display,
    get_or_create_pending_device,
    get_secret,
    user_has_mfa,
)


@method_decorator(never_cache, name="dispatch")
@method_decorator(login_required, name="dispatch")
class MFASetupView(View):
    template_name = "mfa/setup.html"

    def _context(self, device, form):
        return {
            "form": form,
            "qr_data_uri": build_qr_data_uri(build_provisioning_uri(device)),
            "secret_display": format_secret_for_display(get_secret(device)),
        }

    def get(self, request):
        if user_has_mfa(request.user):
            messages.info(request, "MFA është tashmë aktiv për këtë llogari.")
            return redirect("accounts:profile")

        device = get_or_create_pending_device(request.user)
        return render(request, self.template_name, self._context(device, TOTPCodeForm()))

    def post(self, request):
        if user_has_mfa(request.user):
            return redirect("accounts:profile")

        device = get_or_create_pending_device(request.user)
        form = TOTPCodeForm(request.POST)

        if form.is_valid() and confirm_device(device, form.cleaned_data["code"]):
            record_event(
                SecurityEvent.EventType.MFA_ENABLED,
                request=request,
                user=request.user,
                metadata={"method": "totp"},
            )
            messages.success(request, "MFA u aktivizua me sukses.")
            return redirect("accounts:profile")

        record_event(
            SecurityEvent.EventType.MFA_CHALLENGE_FAILED,
            request=request,
            user=request.user,
            success=False,
            metadata={"stage": "SETUP", "reason": "invalid_code"},
        )
        messages.error(
            request,
            "Kodi nuk është i saktë. Kontrollo që ora e telefonit është automatike dhe provo sërish.",
        )
        return render(request, self.template_name, self._context(device, TOTPCodeForm()))