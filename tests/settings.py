"""Minimal Django settings for palm-django tests."""

SECRET_KEY = "test-secret-key-not-for-production"
DEBUG = True
USE_TZ = True

INSTALLED_APPS = [
    "django.contrib.contenttypes",
    "palm_django",
    "tests.palm_sample",
]

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    }
}

PALM = {
    "LOAD_EXAMPLE_DEFINITIONS": False,
    "REBUILD_PROJECTIONS_ON_STARTUP": False,
    "ENABLE_COMPENSATION": False,
    "ENABLE_OUTBOX_SERVICE": False,
}

ROOT_URLCONF = []
MIDDLEWARE = []
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"