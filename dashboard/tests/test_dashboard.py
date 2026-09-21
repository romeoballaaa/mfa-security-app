from django.test import TestCase
from django.urls import reverse

from accounts.tests.factories import create_user, enable_mfa
from audit.models import SecurityEvent
from audit.services import record_event
from dashboard.services.metrics import summary

E = SecurityEvent.EventType


class HistoryTests(TestCase):
    def test_history_shows_only_own_events(self):
        liam = create_user("liam")
        mia = create_user("mia")
        record_event(E.LOGIN_SUCCESS, user=liam)
        record_event(E.LOGOUT, user=mia)

        self.client.force_login(liam)
        events = list(self.client.get(reverse("dashboard:history")).context["page"])

        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].user, liam)

    def test_invalid_filter_is_ignored(self):
        self.client.force_login(create_user("nina"))
        response = self.client.get(reverse("dashboard:history"), {"type": "<script>"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["selected"], "")


class MetricsTests(TestCase):
    def test_blocked_failed_and_mfa_are_counted_separately(self):
        record_event(E.LOGIN_FAILED, success=False, metadata={"reason": "bad_credentials"})
        record_event(E.LOGIN_FAILED, success=False, metadata={"reason": "identifier_locked"})
        record_event(E.MFA_CHALLENGE_FAILED, success=False, metadata={"stage": "LOGIN", "reason": "invalid_code"})
        record_event(E.MFA_CHALLENGE_FAILED, success=False, metadata={"stage": "SETUP", "reason": "invalid_code"})

        stats = summary(30)
        self.assertEqual(stats["failed_logins"], 1)
        self.assertEqual(stats["blocked_attempts"], 1)
        self.assertEqual(stats["failed_mfa"], 1)

    def test_mfa_adoption_rate(self):
        enable_mfa(create_user("olga"))
        create_user("paul")

        stats = summary(30)
        self.assertEqual(stats["total_users"], 2)
        self.assertEqual(stats["mfa_users"], 1)
        self.assertEqual(stats["mfa_adoption_pct"], 50.0)