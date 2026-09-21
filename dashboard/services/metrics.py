from datetime import timedelta

from django.contrib.auth import get_user_model
from django.db.models import Count, Q
from django.db.models.functions import TruncDate
from django.utils import timezone

from audit.models import SecurityEvent
from mfa.models import MFADevice
from security.services.lockout import is_user_locked

E = SecurityEvent.EventType
BLOCK_REASONS = ["identifier_locked", "ip_locked", "locked"]


def _since(days):
    return timezone.now() - timedelta(days=days)


def _avg_mfa_seconds(events):
    values = []
    rows = events.filter(
        event_type=E.LOGIN_SUCCESS,
        metadata__stage="MFA",
    ).values_list("metadata", flat=True)

    for metadata in rows:
        try:
            values.append(int(metadata.get("duration_ms", 0)))
        except (TypeError, ValueError):
            continue

    if not values:
        return None
    return round(sum(values) / len(values) / 1000, 1)


def summary(days=30):
    user_model = get_user_model()
    events = SecurityEvent.objects.filter(created_at__gte=_since(days))

    total_users = user_model.objects.count()
    mfa_users = MFADevice.objects.filter(is_confirmed=True).count()

    blocked_attempts = events.filter(
        Q(event_type=E.LOGIN_FAILED, metadata__reason__in=BLOCK_REASONS)
        | Q(event_type=E.MFA_CHALLENGE_FAILED, metadata__reason="locked")
    ).count()

    failed_logins = (
        events.filter(event_type=E.LOGIN_FAILED)
        .exclude(metadata__reason__in=BLOCK_REASONS)
        .count()
    )

    failed_mfa = (
        events.filter(event_type=E.MFA_CHALLENGE_FAILED, metadata__stage="LOGIN")
        .exclude(metadata__reason="locked")
        .count()
    )

    return {
        "period_days": days,
        "total_users": total_users,
        "mfa_users": mfa_users,
        "non_mfa_users": total_users - mfa_users,
        "mfa_adoption_pct": round(100 * mfa_users / total_users, 1) if total_users else 0,
        "successful_logins": events.filter(event_type=E.LOGIN_SUCCESS).count(),
        "failed_logins": failed_logins,
        "failed_mfa": failed_mfa,
        "blocked_attempts": blocked_attempts,
        "lockouts": events.filter(event_type=E.ACCOUNT_LOCKED).count(),
        "locked_now": sum(1 for user in user_model.objects.all() if is_user_locked(user)),
        "unauthorized": events.filter(event_type=E.UNAUTHORIZED_ACCESS).count(),
        "avg_mfa_seconds": _avg_mfa_seconds(events),
    }


def logins_per_day(days=14):
    rows = (
        SecurityEvent.objects.filter(
            created_at__gte=_since(days),
            event_type__in=[E.LOGIN_SUCCESS, E.LOGIN_FAILED],
        )
        .annotate(day=TruncDate("created_at"))
        .values("day", "event_type")
        .annotate(total=Count("id"))
        .order_by()
    )

    today = timezone.localdate()
    days_list = [today - timedelta(days=offset) for offset in range(days - 1, -1, -1)]
    success = {day: 0 for day in days_list}
    failed = {day: 0 for day in days_list}

    for row in rows:
        target = success if row["event_type"] == E.LOGIN_SUCCESS else failed
        if row["day"] in target:
            target[row["day"]] = row["total"]

    return {
        "labels": [day.strftime("%d/%m") for day in days_list],
        "success": [success[day] for day in days_list],
        "failed": [failed[day] for day in days_list],
    }


def events_by_type(days=30):
    rows = (
        SecurityEvent.objects.filter(created_at__gte=_since(days))
        .values("event_type")
        .annotate(total=Count("id"))
        .order_by("-total")
    )
    names = dict(E.choices)
    return {
        "labels": [names.get(row["event_type"], row["event_type"]) for row in rows],
        "values": [row["total"] for row in rows],
    }


def chart_payload(stats, days=30):
    return {
        "mfa": {
            "labels": ["Me MFA", "Pa MFA"],
            "values": [stats["mfa_users"], stats["non_mfa_users"]],
        },
        "auth": {
            "labels": ["Login të suksesshëm", "Login të dështuar", "MFA të dështuar", "Të bllokuara"],
            "values": [
                stats["successful_logins"],
                stats["failed_logins"],
                stats["failed_mfa"],
                stats["blocked_attempts"],
            ],
        },
        "per_day": logins_per_day(14),
        "by_type": events_by_type(days),
    }