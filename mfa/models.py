from django.conf import settings
from django.db import models


class MFADevice(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="mfa_device",
    )
    secret_encrypted = models.TextField()
    is_confirmed = models.BooleanField(default=False)
    confirmed_at = models.DateTimeField(null=True, blank=True)
    last_used_step = models.BigIntegerField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=models.Q(is_confirmed=False, confirmed_at__isnull=True)
                | models.Q(is_confirmed=True, confirmed_at__isnull=False),
                name="mfadevice_confirmed_requires_timestamp",
            )
        ]

    def __str__(self):
        state = "confirmed" if self.is_confirmed else "pending"
        return f"MFADevice({self.user_id}, {state})"


class RecoveryCode(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="recovery_codes",
    )
    code_hash = models.CharField(max_length=64, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    used_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=["user", "used_at"]),
        ]

    @property
    def is_used(self):
        return self.used_at is not None

    def __str__(self):
        state = "used" if self.is_used else "active"
        return f"RecoveryCode({self.user_id}, {state})"