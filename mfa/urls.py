from django.urls import path

from .views import MFASetupView

app_name = "mfa"

urlpatterns = [
    path("setup/", MFASetupView.as_view(), name="setup"),
]