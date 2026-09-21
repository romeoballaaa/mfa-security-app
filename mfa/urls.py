from django.urls import path

from .views import (
    MFADisableView,
    MFARecoveryVerifyView,
    MFASetupView,
    MFAVerifyView,
    RecoveryCodesRegenerateView,
)

app_name = "mfa"

urlpatterns = [
    path("setup/", MFASetupView.as_view(), name="setup"),
    path("verify/", MFAVerifyView.as_view(), name="verify"),
    path("recovery/", MFARecoveryVerifyView.as_view(), name="recovery"),
    path("disable/", MFADisableView.as_view(), name="disable"),
    path("recovery-codes/regenerate/", RecoveryCodesRegenerateView.as_view(), name="regenerate"),
]