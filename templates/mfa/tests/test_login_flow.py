import time

from django.test import TestCase, override_settings
from django.urls import reverse

from accounts.tests.factories import (
    code_at,
    create_user,
    enable_mfa,
    is_logged_in,
    post_login,
    post_totp,
    wrong_code,
)
from audit.models import SecurityEvent
from mfa.services.challenge import SESSION_STARTED_KEY

E = SecurityEvent.EventType


class TwoFactorLoginTests(TestCase):
    def setUp(self):
        self.user = create_user("grace")
        self.secret = enable_mfa(self.user)

    def test_password_alone_gives_no_access(self):
        response = post_login(self.client, "grace")
        self.assertRedirects(response, reverse("mfa:verify"))
        self.assertFalse(is_logged_in(self.client))

        for url in (reverse("accounts:profile"), reverse("dashboard:history")):
            protected = self.client.get(url)
            self.assertEqual(protected.status_code, 302)
            self.assertIn(reverse("accounts:login"), protected["Location"])

    def test_session_key_rotates_at_password_stage(self):
        session = self.client.session
        session["probe"] = "x"
        session.save()
        before = session.session_key

        post_login(self.client, "grace")
        self.assertNotEqual(before, self.client.session.session_key)

    def test_correct_totp_completes_login(self):
        post_login(self.client, "grace")
        response = post_totp(self.client, code_at(self.secret))

        self.assertRedirects(response, reverse("accounts:profile"))
        self.assertTrue(is_logged_in(self.client))

        types = set(SecurityEvent.objects.values_list("event_type", flat=True))
        self.assertTrue({E.MFA_CHALLENGE_ISSUED, E.MFA_CHALLENGE_SUCCESS, E.LOGIN_SUCCESS} <= types)

        login_event = SecurityEvent.objects.get(event_type=E.LOGIN_SUCCESS)
        self.assertEqual(login_event.metadata["stage"], "MFA")
        self.assertIn("duration_ms", login_event.metadata)

    def test_wrong_totp_is_rejected(self):
        post_login(self.client, "grace")
        post_totp(self.client, wrong_code(self.secret))

        self.assertFalse(is_logged_in(self.client))
        self.assertTrue(
            SecurityEvent.objects.filter(
                event_type=E.MFA_CHALLENGE_FAILED, metadata__reason="invalid_code"
            ).exists()
        )

    def test_verify_without_challenge_redirects(self):
        response = self.client.get(reverse("mfa:verify"))
        self.assertRedirects(response, reverse("accounts:login"))

    def test_expired_challenge_is_rejected(self):
        post_login(self.client, "grace")
        session = self.client.session
        session[SESSION_STARTED_KEY] = time.time() - 10_000
        session.save()

        response = post_totp(self.client, code_at(self.secret))
        self.assertRedirects(response, reverse("accounts:login"))
        self.assertFalse(is_logged_in(self.client))

    @override_settings(MFA_CHALLENGE_MAX_ATTEMPTS=3, LOCKOUT_MAX_FAILURES=100)
    def test_challenge_cancelled_after_max_attempts(self):
        post_login(self.client, "grace")
        for _ in range(3):
            post_totp(self.client, wrong_code(self.secret))

        response = post_totp(self.client, code_at(self.secret))
        self.assertRedirects(response, reverse("accounts:login"))
        self.assertFalse(is_logged_in(self.client))

    def test_replayed_totp_is_rejected_at_login(self):
        code = code_at(self.secret)
        post_login(self.client, "grace")
        post_totp(self.client, code)
        self.assertTrue(is_logged_in(self.client))

        self.client.post(reverse("accounts:logout"))
        post_login(self.client, "grace")
        post_totp(self.client, code)

        self.assertFalse(is_logged_in(self.client))
        self.assertTrue(
            SecurityEvent.objects.filter(
                event_type=E.MFA_CHALLENGE_FAILED, metadata__reason="replay"
            ).exists()
        )