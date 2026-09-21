import base64
import hmac
import io

import pyotp
import qrcode
import qrcode.image.svg
from django.conf import settings
from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from mfa.models import MFADevice
from mfa.services.crypto import decrypt_secret, encrypt_secret

TOTP_DIGITS = 6

VERIFY_OK = "ok"
VERIFY_INVALID = "invalid_code"
VERIFY_REPLAY = "replay"


def user_has_mfa(user):
    if not user.is_authenticated:
        return False
    return MFADevice.objects.filter(user=user, is_confirmed=True).exists()


def get_confirmed_device(user):
    return MFADevice.objects.filter(user=user, is_confirmed=True).first()


def get_or_create_pending_device(user):
    device, _ = MFADevice.objects.get_or_create(
        user=user,
        defaults={"secret_encrypted": encrypt_secret(pyotp.random_base32())},
    )
    return device


def get_secret(device):
    return decrypt_secret(device.secret_encrypted)


def build_provisioning_uri(device):
    return pyotp.TOTP(get_secret(device)).provisioning_uri(
        name=device.user.email or device.user.username,
        issuer_name=settings.MFA_ISSUER_NAME,
    )


def build_qr_data_uri(provisioning_uri):
    image = qrcode.make(
        provisioning_uri,
        image_factory=qrcode.image.svg.SvgPathImage,
        box_size=10,
    )
    buffer = io.BytesIO()
    image.save(buffer)
    encoded = base64.b64encode(buffer.getvalue()).decode("ascii")
    return f"data:image/svg+xml;base64,{encoded}"


def format_secret_for_display(secret):
    return " ".join(secret[i:i + 4] for i in range(0, len(secret), 4))


def normalize_code(code):
    return "".join((code or "").split())


def match_totp_step(secret, code, now=None):
    code = normalize_code(code)
    if len(code) != TOTP_DIGITS or not code.isdigit():
        return None

    totp = pyotp.TOTP(secret, digits=TOTP_DIGITS)
    current_step = totp.timecode(now or timezone.now())
    window = settings.MFA_TOTP_VALID_WINDOW

    for offset in range(-window, window + 1):
        step = current_step + offset
        if hmac.compare_digest(totp.generate_otp(step), code):
            return step

    return None


def verify_code(device, code, now=None):
    step = match_totp_step(get_secret(device), code, now=now)
    if step is None:
        return VERIFY_INVALID

    updated = (
        MFADevice.objects.filter(pk=device.pk)
        .filter(Q(last_used_step__isnull=True) | Q(last_used_step__lt=step))
        .update(last_used_step=step)
    )
    if updated == 1:
        return VERIFY_OK
    return VERIFY_REPLAY


def verify_and_consume(device, code, now=None):
    return verify_code(device, code, now=now) == VERIFY_OK


def confirm_device(device, code):
    with transaction.atomic():
        if not verify_and_consume(device, code):
            return False
        MFADevice.objects.filter(pk=device.pk).update(
            is_confirmed=True,
            confirmed_at=timezone.now(),
        )
    return True