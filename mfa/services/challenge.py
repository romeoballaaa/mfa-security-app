import time

from django.conf import settings
from django.contrib.auth import get_user_model

SESSION_USER_KEY = "pre_mfa_user_id"
SESSION_BACKEND_KEY = "pre_mfa_backend"
SESSION_STARTED_KEY = "pre_mfa_started_at"
SESSION_ATTEMPTS_KEY = "pre_mfa_attempts"

CHALLENGE_KEYS = (
    SESSION_USER_KEY,
    SESSION_BACKEND_KEY,
    SESSION_STARTED_KEY,
    SESSION_ATTEMPTS_KEY,
)


def start_challenge(request, user):
    request.session.cycle_key()
    request.session[SESSION_USER_KEY] = user.pk
    request.session[SESSION_BACKEND_KEY] = getattr(user, "backend", None)
    request.session[SESSION_STARTED_KEY] = time.time()
    request.session[SESSION_ATTEMPTS_KEY] = 0


def clear_challenge(request):
    for key in CHALLENGE_KEYS:
        request.session.pop(key, None)


def challenge_elapsed_seconds(request):
    started = request.session.get(SESSION_STARTED_KEY)
    if started is None:
        return None
    return time.time() - started


def get_challenge_backend(request):
    return request.session.get(SESSION_BACKEND_KEY)


def get_challenge_user(request):
    user_id = request.session.get(SESSION_USER_KEY)
    if user_id is None:
        return None

    elapsed = challenge_elapsed_seconds(request)
    if elapsed is None or elapsed > settings.MFA_CHALLENGE_TIMEOUT_SECONDS:
        clear_challenge(request)
        return None

    user = get_user_model().objects.filter(pk=user_id, is_active=True).first()
    if user is None:
        clear_challenge(request)
    return user


def register_failed_attempt(request):
    attempts = request.session.get(SESSION_ATTEMPTS_KEY, 0) + 1
    request.session[SESSION_ATTEMPTS_KEY] = attempts
    return attempts