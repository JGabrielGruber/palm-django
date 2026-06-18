"""
palm-django — first-class Django integration for Palm Engine.

Add ``palm_django`` to ``INSTALLED_APPS`` to bootstrap a process-wide
:class:`~palm.app.host.ApplicationHost`` and auto-discover Palm definitions
from your Django apps.

Quick start::

    # settings.py
    INSTALLED_APPS = [
        # ...
        "palm_django",
    ]

    PALM = {
        "LOAD_EXAMPLE_DEFINITIONS": False,
    }

    # views.py or tasks.py
    from palm_django import get_host

    job = get_host().submit_flow("my_flow")
"""

from __future__ import annotations

from typing import Any

__version__ = "0.8.2"

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
    "DjangoModelProvider",
    "DjangoStorageBackend",
    "PalmResourceModel",
    "as_palm_resource",
    "bootstrap_palm",
    "build_palm_settings_dict",
    "django_atomic",
    "ensure_registered",
    "get_app",
    "get_django_integration_settings",
    "get_host",
    "get_palm_settings",
    "get_runtime",
    "is_palm_started",
    "palm_atomic",
    "palm_model_saved",
    "palm_resource_invoked",
    "register_django_storage",
    "shutdown_palm",
    "storage_health_report",
]

_LAZY_EXPORTS = {
    "DjangoStorageBackend": ("palm_django.backends", "DjangoStorageBackend"),
    "DjangoModelProvider": ("palm_django.providers.provider", "DjangoModelProvider"),
    "PalmResourceModel": ("palm_django.resources.base", "PalmResourceModel"),
    "as_palm_resource": ("palm_django.resources.decorator", "as_palm_resource"),
    "storage_health_report": ("palm_django.backends", "storage_health_report"),
    "ensure_registered": ("palm_django.storages", "ensure_registered"),
    "register_django_storage": ("palm_django.storages", "register_django_storage"),
    "palm_atomic": ("palm_django.transactions", "palm_atomic"),
    "django_atomic": ("palm_django.transactions", "django_atomic"),
    "palm_resource_invoked": ("palm_django.signals", "palm_resource_invoked"),
    "palm_model_saved": ("palm_django.signals", "palm_model_saved"),
}


def __getattr__(name: str) -> Any:
    if name in _LAZY_EXPORTS:
        module_path, attr = _LAZY_EXPORTS[name]
        import importlib

        return getattr(importlib.import_module(module_path), attr)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


default_app_config = "palm_django.apps.PalmDjangoConfig"