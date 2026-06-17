"""
Register the Django ORM storage backend with Palm's storage registry.
"""

from __future__ import annotations

from palm.core.registry import storage_registry

from palm_django.backends import DjangoStorageBackend

_REGISTERED = False


def register_django_storage() -> None:
    """Register ``django`` backend with Palm's global storage registry."""
    global _REGISTERED
    if _REGISTERED or "django" in storage_registry.names():
        _REGISTERED = True
        return
    storage_registry.register("django", DjangoStorageBackend)
    _REGISTERED = True


def ensure_registered() -> None:
    """Idempotent registration hook called during Django app startup."""
    register_django_storage()