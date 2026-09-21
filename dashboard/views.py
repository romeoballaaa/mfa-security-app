from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.shortcuts import render
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.cache import never_cache

from accounts.permissions import admin_required
from audit.models import SecurityEvent

from .services.metrics import chart_payload, summary


@method_decorator(never_cache, name="dispatch")
@method_decorator(login_required, name="dispatch")
class SecurityHistoryView(View):
    template_name = "dashboard/history.html"

    def get(self, request):
        events = request.user.security_events.all()

        selected = request.GET.get("type", "")
        valid_types = {value for value, _ in SecurityEvent.EventType.choices}
        if selected in valid_types:
            events = events.filter(event_type=selected)
        else:
            selected = ""

        page = Paginator(events, 25).get_page(request.GET.get("page"))

        return render(
            request,
            self.template_name,
            {
                "page": page,
                "selected": selected,
                "event_types": SecurityEvent.EventType.choices,
            },
        )


@method_decorator(never_cache, name="dispatch")
@method_decorator(admin_required, name="dispatch")
class AdminSecurityDashboardView(View):
    template_name = "dashboard/admin_dashboard.html"

    def get(self, request):
        days = 30
        stats = summary(days)
        return render(
            request,
            self.template_name,
            {
                "stats": stats,
                "charts": chart_payload(stats, days),
                "recent_events": SecurityEvent.objects.select_related("user")[:20],
            },
        )