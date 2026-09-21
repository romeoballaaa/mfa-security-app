from django.conf import settings
from django.test import Client, TestCase
from django.urls import reverse

from accounts.tests.factories import PASSWORD, create_user, post_login


class SecurityHeadersTests(TestCase):
    def test_security_headers_on_public_page(self):
        response = self.client.get(reverse("home"))

        self.assertIn("default-src 'self'", response["Content-Security-Policy"])
        self.assertIn("frame-ancestors 'none'", response["Content-Security-Policy"])
        self.assertEqual(response["X-Frame-Options"], "DENY")
        self.assertEqual(response["X-Content-Type-Options"], "nosniff")
        self.assertEqual(response["Referrer-Policy"], "same-origin")
        self.assertIn("camera=()", response["Permissions-Policy"])

    def test_login_without_csrf_token_is_rejected(self):
        create_user("jack")
        client = Client(enforce_csrf_checks=True)
        response = client.post(
            reverse("accounts:login"),
            {"identifier": "jack", "password": PASSWORD},
        )
        self.assertEqual(response.status_code, 403)
        self.assertNotIn("_auth_user_id", client.session)

    def test_session_cookie_flags(self):
        create_user("kate")
        post_login(self.client, "kate")
        cookie = self.client.cookies[settings.SESSION_COOKIE_NAME]
        self.assertTrue(cookie["httponly"])
        self.assertEqual(cookie["samesite"], "Lax")