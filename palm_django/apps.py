"""
Django AppConfig — wires Palm Engine into the Django application lifecycle.
"""

from __future__ import annotations

from django.apps import AppConfig


class PalmDjangoConfig(AppConfig):
    """Bootstrap Palm Engine when Django finishes loading apps."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "palm_django"
    verbose_name = "Palm Engine"

    def ready(self) -> None:
        from palm_django import checks  # noqa: F401
        from palm_django.runtime import bootstrap_palm

        bootstrap_palm()