from django.conf import settings
from django.db import models


class LoginAttempt(models.Model):
    class Stage(models.TextChoices):
        PASSWORD = "PASSWORD", "Password"
        TOTP = "TOTP", "TOTP"
        RECOVERY = "RECOVERY", "Recovery code"
        REAUTH = "REAUTH", "Re-authentication"
        ADMIN_UNLOCK = "ADMIN_UNLOCK", "Admin unlock"

    identifier = models.CharField(max_length=64)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="login_attempts",
    )
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    stage = models.CharField(max_length=16, choices=Stage.choices)
    success = models.BooleanField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["identifier", "created_at"]),
            models.Index(fields=["ip_address", "created_at"]),
        ]

    def __str__(self):
        state = "ok" if self.success else "fail"
        return f"{self.created_at:%Y-%m-%d %H:%M:%S} {self.stage} {state}"