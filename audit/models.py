from django.conf import settings
from django.db import models


class SecurityEvent(models.Model):
    class EventType(models.TextChoices):
        USER_REGISTERED = "USER_REGISTERED", "User registered"
        LOGIN_SUCCESS = "LOGIN_SUCCESS", "Login success"
        LOGIN_FAILED = "LOGIN_FAILED", "Login failed"
        LOGOUT = "LOGOUT", "Logout"
        MFA_CHALLENGE_SUCCESS = "MFA_CHALLENGE_SUCCESS", "MFA challenge success"
        MFA_CHALLENGE_FAILED = "MFA_CHALLENGE_FAILED", "MFA challenge failed"
        MFA_ENABLED = "MFA_ENABLED", "MFA enabled"
        MFA_DISABLED = "MFA_DISABLED", "MFA disabled"
        RECOVERY_CODE_USED = "RECOVERY_CODE_USED", "Recovery code used"
        RECOVERY_CODES_REGENERATED = "RECOVERY_CODES_REGENERATED", "Recovery codes regenerated"
        PASSWORD_CHANGED = "PASSWORD_CHANGED", "Password changed"
        ACCOUNT_LOCKED = "ACCOUNT_LOCKED", "Account locked"
        ACCOUNT_UNLOCKED = "ACCOUNT_UNLOCKED", "Account unlocked"
        UNAUTHORIZED_ACCESS = "UNAUTHORIZED_ACCESS", "Unauthorized access attempt"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="security_events",
    )
    event_type = models.CharField(max_length=32, choices=EventType.choices)
    success = models.BooleanField(default=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.CharField(max_length=255, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["event_type", "created_at"]),
            models.Index(fields=["user", "created_at"]),
            models.Index(fields=["created_at"]),
        ]

    def __str__(self):
        return f"{self.created_at:%Y-%m-%d %H:%M:%S} {self.event_type}"