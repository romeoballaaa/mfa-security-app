import statistics
import time

from django.test import Client
from django.urls import reverse

from accounts.tests.factories import PASSWORD, code_at, wrong_code

ATTEMPTS_PER_SCENARIO = 20
TIMING_SAMPLES = 20


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


def _stats(values):
    if not values:
        return {"mean": None, "median": None, "stdev": None}
    return {
        "mean": round(statistics.mean(values), 1),
        "median": round(statistics.median(values), 1),
        "stdev": round(statistics.stdev(values), 1) if len(values) > 1 else 0.0,
    }


def scenario_a_wrong_password(user_factory):
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


def scenario_b_compromised_no_mfa(user_factory):
    user = user_factory("exp_b_user")
    breaches = 0
    for _ in range(ATTEMPTS_PER_SCENARIO):
        client = _fresh_client()
        _password_login(client, user.username, PASSWORD)
        if _is_authenticated(client):
            breaches += 1
    return {
        "attempts": ATTEMPTS_PER_SCENARIO,
        "breaches": breaches,
        "note": "Kontroll: fjalekalim i sakte (i komprometuar), llogari pa MFA.",
    }


def scenario_c_compromised_with_mfa(user_factory):
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
        "note": "Fjalekalim i sakte (i komprometuar), llogari me MFA, TOTP i gabuar.",
    }


def scenario_d_legitimate_mfa_login(user_factory):
    successes = 0
    for i in range(ATTEMPTS_PER_SCENARIO):
        user, secret = user_factory(f"exp_d_{i:02d}", with_mfa=True)
        client = _fresh_client()
        _password_login(client, user.username, PASSWORD)
        _totp_step(client, code_at(secret))
        if _is_authenticated(client):
            successes += 1
    return {
        "attempts": ATTEMPTS_PER_SCENARIO,
        "successes": successes,
        "note": "20 llogari me MFA: fjalekalim + TOTP te sakte.",
    }


def scenario_e_repeated_wrong_password(user_factory):
    user = user_factory("exp_e_user")
    client = _fresh_client()
    blocked_at = None
    for i in range(1, ATTEMPTS_PER_SCENARIO + 1):
        response = _password_login(client, user.username, "wrong-password-xyz")
        content = response.content.decode(errors="ignore")
        if "Shumë tentativa" in content:
            blocked_at = i
            break
    return {
        "attempts_until_block": blocked_at,
        "note": "Bllokim sipas llogarise pas deshtimeve.",
    }


def scenario_f_repeated_wrong_totp(user_factory):
    user, secret = user_factory("exp_f_user", with_mfa=True)
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


def scenario_g_expired_totp(user_factory):
    user, secret = user_factory("exp_g_user", with_mfa=True)
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


def scenario_h_lockout(user_factory):
    user = user_factory("exp_h_user")
    allowed = 0
    for _ in range(ATTEMPTS_PER_SCENARIO):
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


def scenario_i_unauthorized_access(user_factory):
    user = user_factory("exp_i_user")
    forbidden = 0
    for _ in range(ATTEMPTS_PER_SCENARIO):
        client = _fresh_client()
        _password_login(client, user.username, PASSWORD)
        response = client.get(reverse("dashboard:admin"))
        if response.status_code == 403:
            forbidden += 1
    return {
        "attempts": ATTEMPTS_PER_SCENARIO,
        "forbidden": forbidden,
        "note": "User pa rol ADMIN kunder dashboard-it.",
    }


def scenario_j_timing(user_factory):
    warmup = user_factory("exp_j_warmup")
    _password_login(_fresh_client(), warmup.username, PASSWORD)

    password_only = []
    for i in range(TIMING_SAMPLES):
        user = user_factory(f"exp_jp_{i:02d}")
        client = _fresh_client()
        start = time.perf_counter()
        _password_login(client, user.username, PASSWORD)
        password_only.append((time.perf_counter() - start) * 1000)

    mfa_total = []
    totp_step = []
    for i in range(TIMING_SAMPLES):
        user, secret = user_factory(f"exp_jm_{i:02d}", with_mfa=True)
        code = code_at(secret)
        client = _fresh_client()
        start = time.perf_counter()
        _password_login(client, user.username, PASSWORD)
        middle = time.perf_counter()
        _totp_step(client, code)
        end = time.perf_counter()
        if _is_authenticated(client):
            mfa_total.append((end - start) * 1000)
            totp_step.append((end - middle) * 1000)

    p = _stats(password_only)
    m = _stats(mfa_total)
    t = _stats(totp_step)
    overhead = round(m["mean"] - p["mean"], 1) if m["mean"] is not None else None

    return {
        "samples": TIMING_SAMPLES,
        "pw_only_mean_ms": p["mean"],
        "pw_only_median_ms": p["median"],
        "pw_only_stdev_ms": p["stdev"],
        "mfa_mean_ms": m["mean"],
        "mfa_median_ms": m["median"],
        "mfa_stdev_ms": m["stdev"],
        "totp_step_mean_ms": t["mean"],
        "totp_step_median_ms": t["median"],
        "mfa_overhead_ms": overhead,
        "mfa_successful_samples": len(mfa_total),
        "note": "Koha e perpunimit ne server (in-process), jo koha e perdoruesit.",
    }


SCENARIOS = {
    "A": ("Wrong password, no MFA", scenario_a_wrong_password),
    "B": ("Compromised password, no MFA (control)", scenario_b_compromised_no_mfa),
    "C": ("Compromised password, MFA enabled, no TOTP", scenario_c_compromised_with_mfa),
    "D": ("Legitimate login: password + TOTP", scenario_d_legitimate_mfa_login),
    "E": ("Repeated incorrect passwords", scenario_e_repeated_wrong_password),
    "F": ("Repeated incorrect TOTP", scenario_f_repeated_wrong_totp),
    "G": ("Expired TOTP", scenario_g_expired_totp),
    "H": ("Account lockout threshold", scenario_h_lockout),
    "I": ("Unauthorized resource access", scenario_i_unauthorized_access),
    "J": ("Authentication time: password vs password + TOTP", scenario_j_timing),
}