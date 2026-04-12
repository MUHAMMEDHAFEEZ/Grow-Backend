"""
settings_test.py — Overrides for test runner (uses SQLite, no external DB needed).
"""
from .settings import *  # noqa: F401, F403

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    }
}

# Faster password hasher for tests
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]
