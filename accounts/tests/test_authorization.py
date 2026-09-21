from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from audit.models import SecurityEvent

from .factories import create_user

User = get_user_model()


class AuthorizationTests(TestCase):
    def setUp(self):
        self.user = create_user("bob")
        self.admin = create_user("carol", role=User.Role.ADMIN)

    def test_anonymous_profile_redirects_to_login(self):
        response = self.client.get(reverse("accounts:profile"))
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("accounts:login"), response["Location"])

    def test_anonymous_admin_dashboard_redirects_to_login(self):
        response = self.client.get(reverse("dashboard:admin"))
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("accounts:login"), response["Location"])

    def test_regular_user_gets_403_and_event(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse("dashboard:admin"))
        self.assertEqual(response.status_code, 403)

        event = SecurityEvent.objects.get(event_type=SecurityEvent.EventType.UNAUTHORIZED_ACCESS)
        self.assertEqual(event.user, self.user)
        self.assertEqual(event.metadata["path"], reverse("dashboard:admin"))

    def test_admin_role_can_open_dashboard(self):
        self.client.force_login(self.admin)
        self.assertEqual(self.client.get(reverse("dashboard:admin")).status_code, 200)

    def test_django_admin_login_redirects_to_mfa_login(self):
        response = self.client.get("/admin/login/")
        self.assertRedirects(
            response, reverse("accounts:login"), fetch_redirect_response=False
        )

    def test_protected_pages_are_not_cached(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse("accounts:profile"))
        self.assertIn("no-store", response["Cache-Control"])