from datetime import timedelta

from django.conf import settings
from django.contrib.auth import get_user_model
from django.db.models import Q
from django.utils import timezone
from django.utils.crypto import salted_hmac

from audit.models import SecurityEvent
from audit.services import record_event
from audit.utils import get_client_ip
from security.models import LoginAttempt

LOCKOUT_MESSAGE = "Shumë tentativa të pasakta. Provo përsëri pas disa minutash."

LOCK_IDENTIFIER = "identifier_locked"
LOCK_IP = "ip_locked"


def canonical_identifier(raw_identifier):
    normalized = (raw_identifier or "").strip().lower()
    if not normalized:
        return "empty"

    user = (
        get_user_model()
        .objects.filter(Q(username__iexact=normalized) | Q(email__iexact=normalized))
        .only("pk")
        .first()
    )
    if user is not None:
        return f"user:{user.pk}"

    digest = salted_hmac("security.identifier", normalized, algorithm="sha256").hexdigest()
    return f"anon:{digest[:32]}"


def identifier_for_user(user):
    return f"user:{user.pk}"


def _user_from_identifier(identifier):
    if not identifier.startswith("user:"):
        return None
    return get_user_model().objects.filter(pk=identifier.split(":", 1)[1]).first()


def _window_start():
    return timezone.now() - timedelta(seconds=settings.LOCKOUT_WINDOW_SECONDS)


def identifier_failure_count(identifier):
    since = _window_start()
    last_success = (
        LoginAttempt.objects.filter(identifier=identifier, success=True, created_at__gt=since)
        .order_by("-created_at")
        .values_list("created_at", flat=True)
        .first()
    )
    if last_success is not None:
        since = last_success

    return LoginAttempt.objects.filter(
        identifier=identifier,
        success=False,
        created_at__gt=since,
    ).count()


def ip_failure_count(ip_address):
    if not ip_address:
        return 0
    return LoginAttempt.objects.filter(
        ip_address=ip_address,
        success=False,
        created_at__gt=_window_start(),
    ).count()


def check_lock(identifier, request):
    if identifier_failure_count(identifier) >= settings.LOCKOUT_MAX_FAILURES:
        return LOCK_IDENTIFIER
    if ip_failure_count(get_client_ip(request)) >= settings.LOCKOUT_MAX_FAILURES_PER_IP:
        return LOCK_IP
    return None


def is_user_locked(user):
    return identifier_failure_count(identifier_for_user(user)) >= settings.LOCKOUT_MAX_FAILURES


def record_failure(identifier, request, stage):
    user = _user_from_identifier(identifier)
    ip_address = get_client_ip(request)

    LoginAttempt.objects.create(
        identifier=identifier,
        user=user,
        ip_address=ip_address,
        stage=stage,
        success=False,
    )

    if identifier_failure_count(identifier) == settings.LOCKOUT_MAX_FAILURES:
        record_event(
            SecurityEvent.EventType.ACCOUNT_LOCKED,
            request=request,
            user=user,
            success=False,
            metadata={"stage": stage, "reason": "identifier_threshold"},
        )

    if ip_address and ip_failure_count(ip_address) == settings.LOCKOUT_MAX_FAILURES_PER_IP:
        record_event(
            SecurityEvent.EventType.ACCOUNT_LOCKED,
            request=request,
            user=None,
            success=False,
            metadata={"stage": stage, "reason": "ip_threshold"},
        )


def record_success(user, request, stage):
    LoginAttempt.objects.create(
        identifier=identifier_for_user(user),
        user=user,
        ip_address=get_client_ip(request),
        stage=stage,
        success=True,
    )


def unlock_user(user, request=None):
    LoginAttempt.objects.create(
        identifier=identifier_for_user(user),
        user=user,
        ip_address=get_client_ip(request),
        stage=LoginAttempt.Stage.ADMIN_UNLOCK,
        success=True,
    )
    record_event(
        SecurityEvent.EventType.ACCOUNT_UNLOCKED,
        request=request,
        user=user,
        metadata={"method": "admin"},
    )