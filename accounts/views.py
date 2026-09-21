from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.cache import never_cache

from audit.models import SecurityEvent
from audit.services import record_event
from mfa.services.totp import user_has_mfa

from .forms import LoginForm, RegistrationForm

GENERIC_LOGIN_ERROR = "Kredencialet nuk janë të sakta."


def _identifier_hint(identifier):
    if not identifier:
        return "empty"
    return f"{identifier[:3]}***({len(identifier)})"


class RegisterView(View):
    template_name = "accounts/register.html"

    def get(self, request):
        if request.user.is_authenticated:
            return redirect("home")
        return render(request, self.template_name, {"form": RegistrationForm()})

    def post(self, request):
        if request.user.is_authenticated:
            return redirect("home")

        form = RegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            record_event(
                SecurityEvent.EventType.USER_REGISTERED,
                request=request,
                user=user,
                metadata={"method": "web_form"},
            )
            messages.success(
                request,
                "Llogaria u krijua me sukses. Tani mund të kyçesh.",
            )
            return redirect("accounts:login")

        messages.error(request, "Korrigjo gabimet e mëposhtme.")
        return render(request, self.template_name, {"form": form})


class LoginView(View):
    template_name = "accounts/login.html"

    def get(self, request):
        if request.user.is_authenticated:
            return redirect("accounts:profile")
        return render(request, self.template_name, {"form": LoginForm()})

    def post(self, request):
        if request.user.is_authenticated:
            return redirect("accounts:profile")

        form = LoginForm(request.POST)

        if not form.is_valid():
            return self._fail(request, form, "", "invalid_form")

        identifier = form.cleaned_data["identifier"]
        password = form.cleaned_data["password"]

        user = authenticate(request, username=identifier, password=password)

        if user is None:
            return self._fail(request, form, identifier, "bad_credentials")

        login(request, user)

        record_event(
            SecurityEvent.EventType.LOGIN_SUCCESS,
            request=request,
            user=user,
            metadata={"stage": "PASSWORD", "method": "password"},
        )

        messages.success(request, f"Mirë se erdhe, {user.username}.")
        return redirect("accounts:profile")

    def _fail(self, request, form, identifier, reason):
        record_event(
            SecurityEvent.EventType.LOGIN_FAILED,
            request=request,
            user=None,
            success=False,
            metadata={
                "stage": "PASSWORD",
                "reason": reason,
                "identifier_hint": _identifier_hint(identifier),
            },
        )
        messages.error(request, GENERIC_LOGIN_ERROR)
        return render(request, self.template_name, {"form": form})


class LogoutView(View):
    def post(self, request):
        user = request.user if request.user.is_authenticated else None

        if user is not None:
            record_event(
                SecurityEvent.EventType.LOGOUT,
                request=request,
                user=user,
            )

        logout(request)
        messages.info(request, "U shkëpute nga sistemi.")
        return redirect("home")


@method_decorator(never_cache, name="dispatch")
@method_decorator(login_required, name="dispatch")
class ProfileView(View):
    template_name = "accounts/profile.html"

    def get(self, request):
        recent_events = request.user.security_events.all()[:10]
        return render(
            request,
            self.template_name,
            {
                "recent_events": recent_events,
                "mfa_enabled": user_has_mfa(request.user),
            },
        )