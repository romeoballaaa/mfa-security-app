from datetime import timedelta

from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from accounts.tests.factories import (
    create_user,
    enable_mfa,
    is_logged_in,
    post_login,
    post_totp,
    wrong_code,
)
from audit.models import SecurityEvent
from security.models import LoginAttempt
from security.services.lockout import LOCKOUT_MESSAGE, unlock_user


@override_settings(
    LOCKOUT_MAX_FAILURES=3,
    LOCKOUT_MAX_FAILURES_PER_IP=1000,
    MFA_CHALLENGE_MAX_ATTEMPTS=10,
)
class LockoutTests(TestCase):
    def setUp(self):
        self.user = create_user("henry")

    def fail(self, identifier="henry", times=1):
        for _ in range(times):
            post_login(self.client, identifier, "wrong-password")

    def test_account_locks_after_threshold(self):
        self.fail(times=3)
        response = post_login(self.client, "henry")
        self.assertContains(response, LOCKOUT_MESSAGE)
        self.assertFalse(is_logged_in(self.client))

    def test_username_and_email_share_counter(self):
        self.fail("henry", 2)
        self.fail("HENRY@example.com", 1)
        response = post_login(self.client, "henry@example.com")
        self.assertContains(response, LOCKOUT_MESSAGE)

    def test_unknown_identifier_is_locked_the_same_way(self):
        self.fail("ghost", 3)
        response = post_login(self.client, "ghost", "anything")
        self.assertContains(response, LOCKOUT_MESSAGE)

    def test_successful_login_resets_counter(self):
        self.fail(times=2)
        post_login(self.client, "henry")
        self.client.post(reverse("accounts:logout"))

        self.fail(times=2)
        post_login(self.client, "henry")
        self.assertTrue(is_logged_in(self.client))

    def test_lock_emits_single_event(self):
        self.fail(times=3)
        post_login(self.client, "henry")
        self.assertEqual(
            SecurityEvent.objects.filter(event_type=SecurityEvent.EventType.ACCOUNT_LOCKED).count(),
            1,
        )

    def test_blocked_attempts_do_not_extend_lock(self):
        self.fail(times=3)
        for _ in range(5):
            post_login(self.client, "henry")
        self.assertEqual(LoginAttempt.objects.filter(success=False).count(), 3)

    def test_admin_unlock_restores_access(self):
        self.fail(times=3)
        unlock_user(self.user)
        post_login(self.client, "henry")
        self.assertTrue(is_logged_in(self.client))
        self.assertTrue(
            SecurityEvent.objects.filter(event_type=SecurityEvent.EventType.ACCOUNT_UNLOCKED).exists()
        )

    def test_lock_expires_after_window(self):
        self.fail(times=3)
        LoginAttempt.objects.update(created_at=timezone.now() - timedelta(hours=1))
        post_login(self.client, "henry")
        self.assertTrue(is_logged_in(self.client))

    def test_totp_failures_count_and_password_does_not_reset(self):
        secret = enable_mfa(self.user)

        post_login(self.client, "henry")
        post_totp(self.client, wrong_code(secret))
        post_totp(self.client, wrong_code(secret))

        post_login(self.client, "henry")
        post_totp(self.client, wrong_code(secret))

        response = post_login(self.client, "henry")
        self.assertContains(response, LOCKOUT_MESSAGE)
        self.assertFalse(is_logged_in(self.client))


@override_settings(LOCKOUT_MAX_FAILURES=100, LOCKOUT_MAX_FAILURES_PER_IP=3)
class IpLockoutTests(TestCase):
    def test_ip_is_blocked_across_accounts(self):
        create_user("ivy")
        for name in ("x1", "x2", "x3"):
            post_login(self.client, name, "wrong-password")

        response = post_login(self.client, "ivy")
        self.assertContains(response, LOCKOUT_MESSAGE)
        self.assertFalse(is_logged_in(self.client))