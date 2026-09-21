from django.test import TestCase
from django.urls import reverse

from accounts.views import GENERIC_LOGIN_ERROR
from audit.models import SecurityEvent

from .factories import create_user, is_logged_in, post_login


class LoginTests(TestCase):
    def setUp(self):
        self.user = create_user("alice")

    def test_login_with_username(self):
        response = post_login(self.client, "alice")
        self.assertRedirects(response, reverse("accounts:profile"))
        self.assertTrue(is_logged_in(self.client))

    def test_login_with_email_case_insensitive(self):
        post_login(self.client, "ALICE@example.com")
        self.assertTrue(is_logged_in(self.client))

    def test_wrong_password_and_unknown_user_get_same_message(self):
        wrong = post_login(self.client, "alice", "wrong-password")
        unknown = post_login(self.client, "nobody", "wrong-password")
        self.assertContains(wrong, GENERIC_LOGIN_ERROR)
        self.assertContains(unknown, GENERIC_LOGIN_ERROR)
        self.assertFalse(is_logged_in(self.client))

    def test_failed_login_audit_has_no_user_and_no_password(self):
        post_login(self.client, "alice", "Leaked-Secret-999")
        event = SecurityEvent.objects.get(event_type=SecurityEvent.EventType.LOGIN_FAILED)
        self.assertIsNone(event.user)
        self.assertNotIn("Leaked-Secret-999", str(event.metadata))
        self.assertNotIn("alice", str(event.metadata))

    def test_login_rotates_session_key(self):
        session = self.client.session
        session["probe"] = "x"
        session.save()
        before = session.session_key

        post_login(self.client, "alice")
        self.assertNotEqual(before, self.client.session.session_key)

    def test_logout_requires_post(self):
        post_login(self.client, "alice")
        self.assertEqual(self.client.get(reverse("accounts:logout")).status_code, 405)
        self.assertTrue(is_logged_in(self.client))

        self.client.post(reverse("accounts:logout"))
        self.assertFalse(is_logged_in(self.client))
        self.assertTrue(
            SecurityEvent.objects.filter(event_type=SecurityEvent.EventType.LOGOUT).exists()
        )

    def test_inactive_user_cannot_login(self):
        self.user.is_active = False
        self.user.save()
        post_login(self.client, "alice")
        self.assertFalse(is_logged_in(self.client))