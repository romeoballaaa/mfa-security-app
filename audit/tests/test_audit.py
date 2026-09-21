from django.contrib import admin
from django.contrib.auth.models import AnonymousUser
from django.test import RequestFactory, TestCase

from accounts.tests.factories import create_user
from audit.models import SecurityEvent
from audit.services import record_event
from audit.utils import get_client_ip

E = SecurityEvent.EventType


class AuditTests(TestCase):
    def test_forbidden_metadata_keys_are_dropped(self):
        event = record_event(
            E.LOGIN_FAILED,
            metadata={
                "reason": "bad_credentials",
                "password": "p",
                "otp_code": "123456",
                "totp_secret": "JBSWY3DP",
                "recovery_code": "abcde-fghjk",
            },
        )
        self.assertEqual(event.metadata, {"reason": "bad_credentials"})

    def test_metadata_values_are_truncated(self):
        event = record_event(E.LOGIN_FAILED, metadata={"reason": "a" * 500})
        self.assertEqual(len(event.metadata["reason"]), 120)

    def test_user_agent_is_truncated(self):
        request = RequestFactory().get("/", HTTP_USER_AGENT="A" * 1000)
        request.user = AnonymousUser()
        event = record_event(E.LOGIN_FAILED, request=request)
        self.assertEqual(len(event.user_agent), 255)
        self.assertEqual(event.ip_address, "127.0.0.1")

    def test_forwarded_for_header_is_ignored(self):
        request = RequestFactory().get(
            "/", REMOTE_ADDR="10.0.0.1", HTTP_X_FORWARDED_FOR="1.2.3.4"
        )
        self.assertEqual(get_client_ip(request), "10.0.0.1")

    def test_security_events_are_read_only_in_admin(self):
        superuser = create_user("root", is_superuser=True, is_staff=True)
        request = RequestFactory().get("/admin/")
        request.user = superuser

        model_admin = admin.site._registry[SecurityEvent]
        self.assertFalse(model_admin.has_add_permission(request))
        self.assertFalse(model_admin.has_change_permission(request))
        self.assertFalse(model_admin.has_delete_permission(request))