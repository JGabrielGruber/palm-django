"""
Palm storage backend registration for Django ORM persistence.
"""

from __future__ import annotations

from palm_django.storages.registry import ensure_registered, register_django_storage

__all__ = ["ensure_registered", "register_django_storage"]