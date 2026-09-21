from django.contrib import admin
from django.urls import include, path
from django.views.generic import RedirectView, TemplateView

urlpatterns = [
    path("", TemplateView.as_view(template_name="home.html"), name="home"),
    path("accounts/", include("accounts.urls")),
    path("mfa/", include("mfa.urls")),
    path("dashboard/", include("dashboard.urls")),
    path(
        "admin/login/",
        RedirectView.as_view(pattern_name="accounts:login", permanent=False),
    ),
    path("admin/", admin.site.urls),
]