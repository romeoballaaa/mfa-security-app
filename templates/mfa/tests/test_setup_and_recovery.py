from django.test import TestCase
from django.urls import reverse

from accounts.tests.factories import (
    PASSWORD,
    code_at,
    create_user,
    enable_mfa,
    is_logged_in,
    post_login,
    wrong_code,
)
from audit.models import SecurityEvent
from mfa.models import MFADevice, RecoveryCode
from mfa.services.crypto import decrypt_secret
from mfa.services.recovery import generate_recovery_codes
from mfa.services.totp import user_has_mfa


class MFASetupTests(TestCase):
    def setUp(self):
        self.user = create_user("erin")
        self.client.force_login(self.user)

    def _pending(self):
        self.client.get(reverse("mfa:setup"))
        device = MFADevice.objects.get(user=self.user)
        return device, decrypt_secret(device.secret_encrypted)

    def test_secret_is_inactive_until_first_code(self):
        device, secret = self._pending()
        self.assertFalse(device.is_confirmed)
        self.assertFalse(user_has_mfa(self.user))
        self.assertNotEqual(device.secret_encrypted, secret)

    def test_same_secret_until_confirmed(self):
        first, _ = self._pending()
        second, _ = self._pending()
        self.assertEqual(first.secret_encrypted, second.secret_encrypted)

    def test_wrong_first_code_does_not_enable(self):
        device, secret = self._pending()
        self.client.post(reverse("mfa:setup"), {"code": wrong_code(secret)})
        device.refresh_from_db()
        self.assertFalse(device.is_confirmed)

    def test_correct_first_code_enables_and_issues_recovery_codes(self):
        _, secret = self._pending()
        response = self.client.post(reverse("mfa:setup"), {"code": code_at(secret)})

        self.assertEqual(response.status_code, 200)
        self.assertTrue(user_has_mfa(self.user))
        self.assertEqual(len(response.context["codes"]), 10)
        self.assertEqual(RecoveryCode.objects.filter(user=self.user).count(), 10)
        self.assertTrue(
            SecurityEvent.objects.filter(event_type=SecurityEvent.EventType.MFA_ENABLED).exists()
        )


class RecoveryCodeTests(TestCase):
    def setUp(self):
        self.user = create_user("frank")
        self.secret = enable_mfa(self.user)
        self.codes = generate_recovery_codes(self.user)

    def _use(self, code):
        post_login(self.client, "frank")
        return self.client.post(reverse("mfa:recovery"), {"code": code})

    def test_codes_are_stored_hashed(self):
        stored = list(RecoveryCode.objects.values_list("code_hash", flat=True))
        for code in self.codes:
            self.assertNotIn(code, stored)
            self.assertNotIn(code.replace("-", ""), stored)

    def test_recovery_code_logs_in_once(self):
        self._use(self.codes[0])
        self.assertTrue(is_logged_in(self.client))

        self.client.post(reverse("accounts:logout"))
        self._use(self.codes[0])
        self.assertFalse(is_logged_in(self.client))
        self.assertEqual(
            SecurityEvent.objects.filter(
                event_type=SecurityEvent.EventType.RECOVERY_CODE_USED
            ).count(),
            1,
        )

    def test_recovery_code_is_normalized(self):
        self._use(self.codes[1].replace("-", "").upper())
        self.assertTrue(is_logged_in(self.client))

    def test_regeneration_invalidates_old_codes(self):
        generate_recovery_codes(self.user)
        self._use(self.codes[2])
        self.assertFalse(is_logged_in(self.client))


class DisableMFATests(TestCase):
    def setUp(self):
        self.user = create_user("gina")
        self.secret = enable_mfa(self.user)
        generate_recovery_codes(self.user)
        self.client.force_login(self.user)

    def test_disable_requires_correct_password(self):
        self.client.post(
            reverse("mfa:disable"),
            {"password": "wrong-password", "code": code_at(self.secret)},
        )
        self.assertTrue(user_has_mfa(self.user))

    def test_disable_requires_valid_totp(self):
        self.client.post(
            reverse("mfa:disable"),
            {"password": PASSWORD, "code": wrong_code(self.secret)},
        )
        self.assertTrue(user_has_mfa(self.user))

    def test_disable_with_password_and_totp(self):
        self.client.post(
            reverse("mfa:disable"),
            {"password": PASSWORD, "code": code_at(self.secret)},
        )
        self.assertFalse(user_has_mfa(self.user))
        self.assertEqual(RecoveryCode.objects.filter(user=self.user).count(), 0)
        self.assertTrue(
            SecurityEvent.objects.filter(event_type=SecurityEvent.EventType.MFA_DISABLED).exists()
        )