"""
palm-django — first-class Django integration for Palm Engine.

Add ``palm_django`` to ``INSTALLED_APPS`` to bootstrap a process-wide
:class:`~palm.app.host.ApplicationHost` and auto-discover Palm definitions
from your Django apps.

Quick start::

    # settings.py
    INSTALLED_APPS = [
        # ...
        "palm_django",
    ]

    PALM = {
        "STORAGE_BACKEND": "memory",
        "LOAD_EXAMPLE_DEFINITIONS": False,
    }

    # views.py or tasks.py
    from palm_django import get_host

    job = get_host().submit_flow("my_flow")
"""

from __future__ import annotations

__version__ = "0.1.0"

from palm_django.runtime import (
    bootstrap_palm,
    get_app,
    get_host,
    get_runtime,
    is_palm_started,
    shutdown_palm,
)
from palm_django.settings import (
    DEFAULT_PALM_SETTINGS,
    build_palm_settings_dict,
    get_django_integration_settings,
    get_palm_settings,
)

__all__ = [
    "__version__",
    "DEFAULT_PALM_SETTINGS",
    "bootstrap_palm",
    "build_palm_settings_dict",
    "get_app",
    "get_django_integration_settings",
    "get_host",
    "get_palm_settings",
    "get_runtime",
    "is_palm_started",
    "shutdown_palm",
]

default_app_config = "palm_django.apps.PalmDjangoConfig"