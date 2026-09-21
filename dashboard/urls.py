from django.urls import path

from .views import AdminSecurityDashboardView, SecurityHistoryView

app_name = "dashboard"

urlpatterns = [
    path("history/", SecurityHistoryView.as_view(), name="history"),
    path("admin/", AdminSecurityDashboardView.as_view(), name="admin"),
]