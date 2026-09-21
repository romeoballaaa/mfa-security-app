from django.urls import path

from .views import MFASetupView, MFAVerifyView

app_name = "mfa"

urlpatterns = [
    path("setup/", MFASetupView.as_view(), name="setup"),
    path("verify/", MFAVerifyView.as_view(), name="verify"),
]