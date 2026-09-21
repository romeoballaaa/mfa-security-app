import pyotp
from django.test import SimpleTestCase, TestCase

from accounts.tests.factories import code_at, create_user, enable_mfa
from mfa.models import MFADevice
from mfa.services.crypto import decrypt_secret, encrypt_secret
from mfa.services.totp import VERIFY_INVALID, VERIFY_OK, VERIFY_REPLAY, verify_code


class CryptoTests(SimpleTestCase):
    def test_roundtrip_and_random_ciphertext(self):
        secret = pyotp.random_base32()
        first = encrypt_secret(secret)
        second = encrypt_secret(secret)

        self.assertNotEqual(first, second)
        self.assertNotIn(secret, first)
        self.assertEqual(decrypt_secret(first), secret)

    def test_tampered_ciphertext_is_rejected(self):
        token = encrypt_secret("JBSWY3DPEHPK3PXP")
        replacement = "A" if token[20] != "A" else "B"
        tampered = token[:20] + replacement + token[21:]
        with self.assertRaises(ValueError):
            decrypt_secret(tampered)


class TotpTests(TestCase):
    def setUp(self):
        self.user = create_user("dave")
        self.secret = enable_mfa(self.user)
        self.device = MFADevice.objects.get(user=self.user)

    def test_current_code_is_accepted(self):
        self.assertEqual(verify_code(self.device, code_at(self.secret)), VERIFY_OK)

    def test_previous_step_within_window_is_accepted(self):
        self.assertEqual(verify_code(self.device, code_at(self.secret, -30)), VERIFY_OK)

    def test_same_code_cannot_be_used_twice(self):
        code = code_at(self.secret)
        self.assertEqual(verify_code(self.device, code), VERIFY_OK)
        self.assertEqual(verify_code(self.device, code), VERIFY_REPLAY)

    def test_older_code_after_newer_is_rejected(self):
        self.assertEqual(verify_code(self.device, code_at(self.secret)), VERIFY_OK)
        self.assertEqual(verify_code(self.device, code_at(self.secret, -30)), VERIFY_REPLAY)

    def test_expired_code_is_rejected(self):
        self.assertEqual(verify_code(self.device, code_at(self.secret, -300)), VERIFY_INVALID)

    def test_malformed_codes_are_rejected(self):
        for bad in ["", "12345", "1234567", "abcdef"]:
            self.assertEqual(verify_code(self.device, bad), VERIFY_INVALID)