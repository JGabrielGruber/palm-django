"""
Register DjangoModelProvider with Palm's provider registry.
"""

from __future__ import annotations

from palm.core.registry import provider_registry

from palm_django.providers.provider import DjangoModelProvider
from palm_django.resources.registry import PROVIDER_NAME

_REGISTERED = False


def register_django_model_provider() -> None:
    global _REGISTERED
    if _REGISTERED or PROVIDER_NAME in provider_registry.names():
        _REGISTERED = True
        return
    provider_registry.register(PROVIDER_NAME, DjangoModelProvider)
    _REGISTERED = True


def ensure_registered() -> None:
    register_django_model_provider()