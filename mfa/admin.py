from django.contrib import admin

from .models import MFADevice, RecoveryCode


@admin.register(MFADevice)
class MFADeviceAdmin(admin.ModelAdmin):
    list_display = ("user", "is_confirmed", "confirmed_at", "created_at")
    list_filter = ("is_confirmed",)
    search_fields = ("user__username", "user__email")
    readonly_fields = ("user", "is_confirmed", "confirmed_at", "last_used_step", "created_at")
    exclude = ("secret_encrypted",)

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False


@admin.register(RecoveryCode)
class RecoveryCodeAdmin(admin.ModelAdmin):
    list_display = ("user", "created_at", "used_at")
    list_filter = ("used_at",)
    search_fields = ("user__username",)
    readonly_fields = ("user", "created_at", "used_at")
    exclude = ("code_hash",)

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False