from django.contrib import admin

from .models import LoginAttempt


@admin.register(LoginAttempt)
class LoginAttemptAdmin(admin.ModelAdmin):
    list_display = ("created_at", "stage", "success", "user", "ip_address", "identifier")
    list_filter = ("stage", "success", "created_at")
    search_fields = ("user__username", "ip_address", "identifier")
    date_hierarchy = "created_at"

    def get_readonly_fields(self, request, obj=None):
        return [field.name for field in self.model._meta.fields]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False