import secrets

from django.conf import settings
from django.db import transaction
from django.utils import timezone
from django.utils.crypto import salted_hmac

from mfa.models import RecoveryCode

ALPHABET = "abcdefghjkmnpqrstuvwxyz23456789"
CODE_LENGTH = 10
HMAC_SALT = "mfa.recovery_code"


def normalize_recovery_code(code):
    return "".join(ch for ch in (code or "").lower() if ch.isalnum())


def hash_recovery_code(normalized_code):
    return salted_hmac(HMAC_SALT, normalized_code, algorithm="sha256").hexdigest()


def _format_code(raw):
    half = CODE_LENGTH // 2
    return f"{raw[:half]}-{raw[half:]}"


def generate_recovery_codes(user):
    raw_codes = [
        "".join(secrets.choice(ALPHABET) for _ in range(CODE_LENGTH))
        for _ in range(settings.MFA_RECOVERY_CODE_COUNT)
    ]

    with transaction.atomic():
        RecoveryCode.objects.filter(user=user).delete()
        RecoveryCode.objects.bulk_create(
            [RecoveryCode(user=user, code_hash=hash_recovery_code(raw)) for raw in raw_codes]
        )

    return [_format_code(raw) for raw in raw_codes]


def use_recovery_code(user, code):
    normalized = normalize_recovery_code(code)
    if len(normalized) != CODE_LENGTH:
        return False

    updated = RecoveryCode.objects.filter(
        user=user,
        code_hash=hash_recovery_code(normalized),
        used_at__isnull=True,
    ).update(used_at=timezone.now())
    return updated == 1


def remaining_recovery_codes(user):
    return RecoveryCode.objects.filter(user=user, used_at__isnull=True).count()