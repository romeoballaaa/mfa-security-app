import logging

from .dev import *  # noqa: F403

RESEARCH_MODE = True

ALLOWED_HOSTS = ["testserver", "127.0.0.1", "localhost"]

LOCKOUT_MAX_FAILURES_PER_IP = 100000

logging.getLogger("django.request").setLevel(logging.CRITICAL)