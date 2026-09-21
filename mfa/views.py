from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.cache import never_cache

from audit.models import SecurityEvent
from audit.services import record_event

from .forms import TOTPCodeForm
from .services.challenge import (
    challenge_elapsed_seconds,
    clear_challenge,
    get_challenge_backend,
    get_challenge_user,
    register_failed_attempt,
)
from .services.totp import (
    VERIFY_INVALID,
    VERIFY_OK,
    build_provisioning_uri,
    build_qr_data_uri,
    confirm_device,
    format_secret_for_display,
    get_confirmed_device,
    get_or_create_pending_device,
    get_secret,
    user_has_mfa,
    verify_code,
)

GENERIC_CODE_ERROR = "Kodi nuk është i saktë."
CHALLENGE_EXPIRED = "Verifikimi skadoi ose nuk ekziston. Kyçu përsëri."


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


@method_decorator(never_cache, name="dispatch")
class MFAVerifyView(View):
    template_name = "mfa/verify.html"

    def _expired(self, request):
        messages.error(request, CHALLENGE_EXPIRED)
        return redirect("accounts:login")

    def get(self, request):
        if request.user.is_authenticated:
            return redirect("accounts:profile")

        if get_challenge_user(request) is None:
            return self._expired(request)

        return render(request, self.template_name, {"form": TOTPCodeForm()})

    def post(self, request):
        if request.user.is_authenticated:
            return redirect("accounts:profile")

        user = get_challenge_user(request)
        if user is None:
            return self._expired(request)

        device = get_confirmed_device(user)
        if device is None:
            clear_challenge(request)
            return self._expired(request)

        form = TOTPCodeForm(request.POST)
        if form.is_valid():
            result = verify_code(device, form.cleaned_data["code"])
        else:
            result = VERIFY_INVALID

        if result == VERIFY_OK:
            elapsed = challenge_elapsed_seconds(request) or 0
            backend = get_challenge_backend(request)
            clear_challenge(request)

            login(request, user, backend=backend)

            record_event(
                SecurityEvent.EventType.MFA_CHALLENGE_SUCCESS,
                request=request,
                user=user,
                metadata={"stage": "LOGIN", "method": "totp"},
            )
            record_event(
                SecurityEvent.EventType.LOGIN_SUCCESS,
                request=request,
                user=user,
                metadata={
                    "stage": "MFA",
                    "method": "password+totp",
                    "duration_ms": int(elapsed * 1000),
                },
            )
            messages.success(request, f"Mirë se erdhe, {user.username}.")
            return redirect("accounts:profile")

        attempts = register_failed_attempt(request)
        record_event(
            SecurityEvent.EventType.MFA_CHALLENGE_FAILED,
            request=request,
            user=user,
            success=False,
            metadata={"stage": "LOGIN", "reason": result},
        )

        if attempts >= settings.MFA_CHALLENGE_MAX_ATTEMPTS:
            clear_challenge(request)
            messages.error(request, "Shumë tentativa të pasakta. Kyçu përsëri.")
            return redirect("accounts:login")

        messages.error(request, GENERIC_CODE_ERROR)
        return render(request, self.template_name, {"form": TOTPCodeForm()})