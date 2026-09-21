from cryptography.fernet import Fernet

from .base import *  # noqa: F403

DEBUG = False

PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.MD5PasswordHasher",
]

MFA_ENCRYPTION_KEYS = [Fernet.generate_key().decode()]

LOCKOUT_MAX_FAILURES_PER_IP = 1000