from django.contrib import messages
from django.shortcuts import redirect, render
from django.views import View

from audit.models import SecurityEvent
from audit.services import record_event

from .forms import RegistrationForm


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
            return redirect("home")

        messages.error(request, "Korrigjo gabimet e mëposhtme.")
        return render(request, self.template_name, {"form": form})