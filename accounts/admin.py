from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from security.services.lockout import is_user_locked, unlock_user

from .models import User


@admin.action(description="Zhblloko llogaritë e zgjedhura")
def unlock_accounts(modeladmin, request, queryset):
    count = 0
    for user in queryset:
        unlock_user(user, request)
        count += 1
    modeladmin.message_user(request, f"U zhbllokuan {count} llogari.")


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ("username", "email", "role", "is_active", "locked", "date_joined")
    list_filter = ("role", "is_active", "is_staff")
    search_fields = ("username", "email")
    actions = [unlock_accounts]
    fieldsets = BaseUserAdmin.fieldsets + (
        ("Roli i aplikacionit", {"fields": ("role",)}),
    )
    add_fieldsets = BaseUserAdmin.add_fieldsets + (
        ("Roli i aplikacionit", {"fields": ("role",)}),
    )

    @admin.display(boolean=True, description="Bllokuar")
    def locked(self, obj):
        return is_user_locked(obj)