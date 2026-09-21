from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.shortcuts import redirect, render
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.cache import never_cache

from audit.models import SecurityEvent
from audit.services import record_event
from security.models import LoginAttempt
from security.services.lockout import (
    LOCKOUT_MESSAGE,
    check_lock,
    identifier_for_user,
    record_failure,
    record_success,
)

from .forms import ReauthForm, RecoveryCodeForm, TOTPCodeForm
from .models import RecoveryCode
from .services.challenge import (
    challenge_elapsed_seconds,
    clear_challenge,
    get_challenge_backend,
    get_challenge_user,
    register_failed_attempt,
)
from .services.recovery import (
    generate_recovery_codes,
    remaining_recovery_codes,
    use_recovery_code,
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
REAUTH_ERROR = "Fjalëkalimi ose kodi nuk është i saktë."


def _complete_mfa_login(request, user, method, stage):
    elapsed = challenge_elapsed_seconds(request) or 0
    backend = get_challenge_backend(request)
    clear_challenge(request)

    record_success(user, request, stage)
    login(request, user, backend=backend)

    record_event(
        SecurityEvent.EventType.LOGIN_SUCCESS,
        request=request,
        user=user,
        metadata={
            "stage": "MFA",
            "method": method,
            "duration_ms": int(elapsed * 1000),
        },
    )


def _locked_challenge(request, user):
    clear_challenge(request)
    record_event(
        SecurityEvent.EventType.MFA_CHALLENGE_FAILED,
        request=request,
        user=user,
        success=False,
        metadata={"stage": "LOGIN", "reason": "locked"},
    )
    messages.error(request, LOCKOUT_MESSAGE)
    return redirect("accounts:login")


def _handle_challenge_failure(request, user, reason, stage, template_name, form_class):
    record_failure(identifier_for_user(user), request, stage)
    attempts = register_failed_attempt(request)
    record_event(
        SecurityEvent.EventType.MFA_CHALLENGE_FAILED,
        request=request,
        user=user,
        success=False,
        metadata={"stage": "LOGIN", "reason": reason},
    )

    if attempts >= settings.MFA_CHALLENGE_MAX_ATTEMPTS:
        clear_challenge(request)
        messages.error(request, "Shumë tentativa të pasakta. Kyçu përsëri.")
        return redirect("accounts:login")

    messages.error(request, GENERIC_CODE_ERROR)
    return render(request, template_name, {"form": form_class()})


def _reauthenticate(user, device, form):
    if device is None or not form.is_valid():
        return VERIFY_INVALID
    if not user.check_password(form.cleaned_data["password"]):
        return "bad_password"
    return verify_code(device, form.cleaned_data["code"])


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
            codes = generate_recovery_codes(request.user)
            record_event(
                SecurityEvent.EventType.MFA_ENABLED,
                request=request,
                user=request.user,
                metadata={"method": "totp"},
            )
            messages.success(request, "MFA u aktivizua me sukses.")
            return render(
                request,
                "mfa/recovery_codes.html",
                {"codes": codes, "first_time": True},
            )

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

    def get(self, request):
        if request.user.is_authenticated:
            return redirect("accounts:profile")
        if get_challenge_user(request) is None:
            messages.error(request, CHALLENGE_EXPIRED)
            return redirect("accounts:login")
        return render(request, self.template_name, {"form": TOTPCodeForm()})

    def post(self, request):
        if request.user.is_authenticated:
            return redirect("accounts:profile")

        user = get_challenge_user(request)
        device = get_confirmed_device(user) if user else None
        if device is None:
            clear_challenge(request)
            messages.error(request, CHALLENGE_EXPIRED)
            return redirect("accounts:login")

        if check_lock(identifier_for_user(user), request):
            return _locked_challenge(request, user)

        form = TOTPCodeForm(request.POST)
        result = verify_code(device, form.cleaned_data["code"]) if form.is_valid() else VERIFY_INVALID

        if result == VERIFY_OK:
            record_event(
                SecurityEvent.EventType.MFA_CHALLENGE_SUCCESS,
                request=request,
                user=user,
                metadata={"stage": "LOGIN", "method": "totp"},
            )
            _complete_mfa_login(request, user, "password+totp", LoginAttempt.Stage.TOTP)
            messages.success(request, f"Mirë se erdhe, {user.username}.")
            return redirect("accounts:profile")

        return _handle_challenge_failure(
            request, user, result, LoginAttempt.Stage.TOTP, self.template_name, TOTPCodeForm
        )


@method_decorator(never_cache, name="dispatch")
class MFARecoveryVerifyView(View):
    template_name = "mfa/recovery_verify.html"

    def get(self, request):
        if request.user.is_authenticated:
            return redirect("accounts:profile")
        if get_challenge_user(request) is None:
            messages.error(request, CHALLENGE_EXPIRED)
            return redirect("accounts:login")
        return render(request, self.template_name, {"form": RecoveryCodeForm()})

    def post(self, request):
        if request.user.is_authenticated:
            return redirect("accounts:profile")

        user = get_challenge_user(request)
        if user is None or get_confirmed_device(user) is None:
            clear_challenge(request)
            messages.error(request, CHALLENGE_EXPIRED)
            return redirect("accounts:login")

        if check_lock(identifier_for_user(user), request):
            return _locked_challenge(request, user)

        form = RecoveryCodeForm(request.POST)
        if form.is_valid() and use_recovery_code(user, form.cleaned_data["code"]):
            record_event(
                SecurityEvent.EventType.RECOVERY_CODE_USED,
                request=request,
                user=user,
                metadata={"stage": "LOGIN", "method": "recovery"},
            )
            _complete_mfa_login(request, user, "password+recovery", LoginAttempt.Stage.RECOVERY)
            remaining = remaining_recovery_codes(user)
            messages.warning(
                request,
                f"U kyçe me një recovery code. Të kanë mbetur {remaining} kode.",
            )
            return redirect("accounts:profile")

        return _handle_challenge_failure(
            request,
            user,
            "invalid_recovery_code",
            LoginAttempt.Stage.RECOVERY,
            self.template_name,
            RecoveryCodeForm,
        )


@method_decorator(never_cache, name="dispatch")
@method_decorator(login_required, name="dispatch")
class MFADisableView(View):
    template_name = "mfa/reauth.html"
    page = {
        "title": "Çaktivizo MFA",
        "description": "Për siguri, konfirmo fjalëkalimin dhe kodin aktual nga authenticator.",
        "button": "Çaktivizo MFA",
        "danger": True,
    }

    def get(self, request):
        if not user_has_mfa(request.user):
            return redirect("accounts:profile")
        return render(request, self.template_name, {"form": ReauthForm(), **self.page})

    def post(self, request):
        device = get_confirmed_device(request.user)
        if device is None:
            return redirect("accounts:profile")

        identifier = identifier_for_user(request.user)
        if check_lock(identifier, request):
            messages.error(request, LOCKOUT_MESSAGE)
            return redirect("accounts:profile")

        form = ReauthForm(request.POST)
        result = _reauthenticate(request.user, device, form)

        if result == VERIFY_OK:
            with transaction.atomic():
                RecoveryCode.objects.filter(user=request.user).delete()
                device.delete()
            record_event(
                SecurityEvent.EventType.MFA_DISABLED,
                request=request,
                user=request.user,
                metadata={"method": "password+totp"},
            )
            messages.success(request, "MFA u çaktivizua.")
            return redirect("accounts:profile")

        record_failure(identifier, request, LoginAttempt.Stage.REAUTH)
        record_event(
            SecurityEvent.EventType.MFA_CHALLENGE_FAILED,
            request=request,
            user=request.user,
            success=False,
            metadata={"stage": "DISABLE", "reason": result},
        )
        messages.error(request, REAUTH_ERROR)
        return render(request, self.template_name, {"form": ReauthForm(), **self.page})


@method_decorator(never_cache, name="dispatch")
@method_decorator(login_required, name="dispatch")
class RecoveryCodesRegenerateView(View):
    template_name = "mfa/reauth.html"
    page = {
        "title": "Rigjenero recovery codes",
        "description": "Kodet e vjetra do të bëhen të pavlefshme. Konfirmo fjalëkalimin dhe kodin aktual.",
        "button": "Rigjenero kodet",
        "danger": False,
    }

    def get(self, request):
        if not user_has_mfa(request.user):
            return redirect("accounts:profile")
        return render(request, self.template_name, {"form": ReauthForm(), **self.page})

    def post(self, request):
        device = get_confirmed_device(request.user)
        if device is None:
            return redirect("accounts:profile")

        identifier = identifier_for_user(request.user)
        if check_lock(identifier, request):
            messages.error(request, LOCKOUT_MESSAGE)
            return redirect("accounts:profile")

        form = ReauthForm(request.POST)
        result = _reauthenticate(request.user, device, form)

        if result == VERIFY_OK:
            codes = generate_recovery_codes(request.user)
            record_event(
                SecurityEvent.EventType.RECOVERY_CODES_REGENERATED,
                request=request,
                user=request.user,
            )
            return render(
                request,
                "mfa/recovery_codes.html",
                {"codes": codes, "first_time": False},
            )

        record_failure(identifier, request, LoginAttempt.Stage.REAUTH)
        record_event(
            SecurityEvent.EventType.MFA_CHALLENGE_FAILED,
            request=request,
            user=request.user,
            success=False,
            metadata={"stage": "REGENERATE", "reason": result},
        )
        messages.error(request, REAUTH_ERROR)
        return render(request, self.template_name, {"form": ReauthForm(), **self.page})