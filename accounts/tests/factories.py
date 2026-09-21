import time

import pyotp
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone

from mfa.models import MFADevice
from mfa.services.crypto import encrypt_secret

PASSWORD = "Test-Password-2026!"


def create_user(username="alice", email=None, password=PASSWORD, **extra):
    return get_user_model().objects.create_user(
        username=username,
        email=email or f"{username}@example.com",
        password=password,
        **extra,
    )


def enable_mfa(user):
    secret = pyotp.random_base32()
    MFADevice.objects.create(
        user=user,
        secret_encrypted=encrypt_secret(secret),
        is_confirmed=True,
        confirmed_at=timezone.now(),
    )
    return secret


def code_at(secret, offset_seconds=0):
    return pyotp.TOTP(secret).at(time.time() + offset_seconds)


def wrong_code(secret):
    valid = {code_at(secret, offset) for offset in (-30, 0, 30)}
    for number in range(1_000_000):
        candidate = f"{number:06d}"
        if candidate not in valid:
            return candidate
    raise AssertionError("Nuk u gjet kod i pavlefshëm.")


def post_login(client, identifier, password=PASSWORD):
    return client.post(
        reverse("accounts:login"),
        {"identifier": identifier, "password": password},
    )


def post_totp(client, code):
    return client.post(reverse("mfa:verify"), {"code": code})


def is_logged_in(client):
    return "_auth_user_id" in client.session