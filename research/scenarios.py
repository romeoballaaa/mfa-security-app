import time

import pyotp
from django.test import Client
from django.urls import reverse

from accounts.tests.factories import PASSWORD, code_at, wrong_code

ATTEMPTS_PER_SCENARIO = 20
ATTEMPTS_TIMED = 2
STEP_PAUSE = 1.1


def _fresh_client():
    return Client()


def _is_authenticated(client):
    return "_auth_user_id" in client.session


def _password_login(client, identifier, password):
    return client.post(
        reverse("accounts:login"),
        {"identifier": identifier, "password": password},
    )


def _totp_step(client, code):
    return client.post(reverse("mfa:verify"), {"code": code})


def _reached_mfa(client, identifier, password):
    _password_login(client, identifier, password)
    response = client.get(reverse("mfa:verify"))
    return response.status_code == 200


def _unique_code(secret, used):
    for _ in range(40):
        code = code_at(secret)
        if code not in used:
            used.add(code)
            return code
        time.sleep(STEP_PAUSE)
    used.add(code_at(secret))
    return code_at(secret)


def scenario_a_password_only(user_factory):
    user = user_factory("exp_a_user")
    breaches = 0
    for _ in range(ATTEMPTS_PER_SCENARIO):
        client = _fresh_client()
        _password_login(client, user.username, "wrong-password-xyz")
        if _is_authenticated(client):
            breaches += 1
    return {
        "attempts": ATTEMPTS_PER_SCENARIO,
        "breaches": breaches,
        "note": "Fjalekalim i gabuar, pa MFA.",
    }


def scenario_b_password_plus_mfa(user_factory):
    user, secret = user_factory("exp_b_user", with_mfa=True)
    successes = 0
    durations = []
    used = set()
    for _ in range(ATTEMPTS_TIMED):
        code = _unique_code(secret, used)
        client = _fresh_client()
        start = time.perf_counter()
        _password_login(client, user.username, PASSWORD)
        _totp_step(client, code)
        durations.append((time.perf_counter() - start) * 1000)
        if _is_authenticated(client):
            successes += 1
    avg = round(sum(durations) / len(durations), 1) if durations else 0
    return {
        "attempts": ATTEMPTS_TIMED,
        "successes": successes,
        "avg_ms": avg,
        "note": "Kredenciale te sakta + TOTP i sakte (kode unike).",
    }


def scenario_c_compromised_password(user_factory):
    user, secret = user_factory("exp_c_user", with_mfa=True)
    breaches = 0
    reached_second_factor = 0
    for _ in range(ATTEMPTS_PER_SCENARIO):
        client = _fresh_client()
        if _reached_mfa(client, user.username, PASSWORD):
            reached_second_factor += 1
        _totp_step(client, wrong_code(secret))
        if _is_authenticated(client):
            breaches += 1
    return {
        "attempts": ATTEMPTS_PER_SCENARIO,
        "reached_second_factor": reached_second_factor,
        "breaches": breaches,
        "note": "Fjalekalim i sakte, TOTP i gabuar.",
    }


def scenario_d_repeated_wrong_password(user_factory):
    user = user_factory("exp_d_user")
    client = _fresh_client()
    blocked_at = None
    for i in range(1, ATTEMPTS_PER_SCENARIO + 1):
        response = _password_login(client, user.username, "wrong-password-xyz")
        content = response.content.decode(errors="ignore")
        if "Shumë tentativa" in content and blocked_at is None:
            blocked_at = i
            break
    return {
        "attempts_until_block": blocked_at,
        "note": "Bllokim sipas llogarise pas deshtimeve.",
    }


def scenario_e_repeated_wrong_totp(user_factory):
    user, secret = user_factory("exp_e_user", with_mfa=True)
    client = _fresh_client()
    _password_login(client, user.username, PASSWORD)
    cancelled_at = None
    for i in range(1, ATTEMPTS_PER_SCENARIO + 1):
        response = _totp_step(client, wrong_code(secret))
        if response.status_code == 302 and reverse("accounts:login") in response.url:
            cancelled_at = i
            break
    return {
        "attempts_until_cancel": cancelled_at,
        "note": "Anulim i sfides pas TOTP-ve te gabuar.",
    }


def scenario_f_expired_totp(user_factory):
    user, secret = user_factory("exp_f_user", with_mfa=True)
    breaches = 0
    for _ in range(ATTEMPTS_PER_SCENARIO):
        client = _fresh_client()
        _password_login(client, user.username, PASSWORD)
        _totp_step(client, code_at(secret, -300))
        if _is_authenticated(client):
            breaches += 1
    return {
        "attempts": ATTEMPTS_PER_SCENARIO,
        "breaches": breaches,
        "note": "Kod TOTP 5 min i vjeter.",
    }


def scenario_g_lockout(user_factory):
    user = user_factory("exp_g_user")
    allowed = 0
    for i in range(1, ATTEMPTS_PER_SCENARIO + 1):
        client = _fresh_client()
        response = _password_login(client, user.username, "wrong-password-xyz")
        content = response.content.decode(errors="ignore")
        if "Shumë tentativa" in content:
            break
        allowed += 1
    return {
        "failures_allowed_before_lock": allowed,
        "note": "Numri i deshtimeve para bllokimit te llogarise.",
    }


def scenario_h_unauthorized_access(user_factory):
    user = user_factory("exp_h_user")
    forbidden = 0
    for _ in range(ATTEMPTS_PER_SCENARIO):
        client = _fresh_client()
        _password_login(client, user.username, PASSWORD)
        response = client.get(reverse("dashboard:admin"))
        if response.status_code == 403:
            forbidden += 1
    return {
        "attempts": ATTEMPTS_TIMED if False else ATTEMPTS_PER_SCENARIO,
        "forbidden": forbidden,
        "note": "User pa rol ADMIN kunder dashboard-it.",
    }


SCENARIOS = {
    "A": ("Password-only authentication", scenario_a_password_only),
    "B": ("Password + MFA", scenario_b_password_plus_mfa),
    "C": ("Compromised password, no TOTP", scenario_c_compromised_password),
    "D": ("Repeated incorrect passwords", scenario_d_repeated_wrong_password),
    "E": ("Repeated incorrect TOTP", scenario_e_repeated_wrong_totp),
    "F": ("Expired/invalid TOTP", scenario_f_expired_totp),
    "G": ("Account lockout / throttling", scenario_g_lockout),
    "H": ("Unauthorized resource access", scenario_h_unauthorized_access),
}