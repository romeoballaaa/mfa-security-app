from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from cryptography.fernet import Fernet, InvalidToken, MultiFernet


def _build_cipher():
    keys = settings.MFA_ENCRYPTION_KEYS
    if not keys:
        raise ImproperlyConfigured(
            "MFA_ENCRYPTION_KEYS nuk është konfiguruar. Shiko .env.example."
        )
    return MultiFernet([Fernet(key.strip()) for key in keys])


def encrypt_secret(plaintext):
    if not plaintext:
        raise ValueError("Secret bosh nuk enkriptohet.")
    return _build_cipher().encrypt(plaintext.encode()).decode()


def decrypt_secret(token):
    if not token:
        raise ValueError("Token bosh nuk dekriptohet.")
    try:
        return _build_cipher().decrypt(token.encode()).decode()
    except InvalidToken as exc:
        raise ValueError("Secret-i nuk mund të dekriptohet me çelësat aktualë.") from exc