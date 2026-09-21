from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from audit.models import SecurityEvent

from .factories import PASSWORD, create_user, is_logged_in

User = get_user_model()


class RegistrationTests(TestCase):
    def register(self, **overrides):
        data = {
            "username": "newuser",
            "email": "new@example.com",
            "password1": PASSWORD,
            "password2": PASSWORD,
        }
        data.update(overrides)
        return self.client.post(reverse("accounts:register"), data)

    def test_registration_stores_hashed_password_and_audits(self):
        response = self.register()
        self.assertRedirects(response, reverse("accounts:login"))

        user = User.objects.get(username="newuser")
        self.assertNotEqual(user.password, PASSWORD)
        self.assertTrue(user.check_password(PASSWORD))
        self.assertTrue(
            SecurityEvent.objects.filter(
                user=user, event_type=SecurityEvent.EventType.USER_REGISTERED
            ).exists()
        )

    def test_email_uniqueness_is_case_insensitive(self):
        create_user("existing", email="taken@example.com")
        response = self.register(email="TAKEN@Example.com")
        self.assertEqual(response.status_code, 200)
        self.assertFalse(User.objects.filter(username="newuser").exists())

    def test_weak_password_is_rejected(self):
        response = self.register(password1="12345678", password2="12345678")
        self.assertEqual(response.status_code, 200)
        self.assertFalse(User.objects.filter(username="newuser").exists())

    def test_registration_does_not_log_in(self):
        self.register()
        self.assertFalse(is_logged_in(self.client))