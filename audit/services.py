from .models import SecurityEvent
from .utils import get_client_ip, get_user_agent

ALLOWED_METADATA_KEYS = {
    "reason",
    "stage",
    "method",
    "identifier_hint",
    "duration_ms",
    "scenario",
    "run_id",
}


def _sanitize_metadata(metadata):
    if not metadata:
        return {}
    clean = {}
    for key, value in metadata.items():
        if key not in ALLOWED_METADATA_KEYS:
            continue
        clean[key] = str(value)[:120]
    return clean


def record_event(
    event_type,
    request=None,
    user=None,
    success=True,
    metadata=None,
):
    if user is None and request is not None:
        request_user = getattr(request, "user", None)
        if request_user is not None and request_user.is_authenticated:
            user = request_user

    return SecurityEvent.objects.create(
        user=user,
        event_type=event_type,
        success=success,
        ip_address=get_client_ip(request),
        user_agent=get_user_agent(request),
        metadata=_sanitize_metadata(metadata),
    )