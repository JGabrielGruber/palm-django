"""
Django AppConfig — wires Palm Engine into the Django application lifecycle.
"""

from __future__ import annotations

from django.apps import AppConfig
from palm.core.exceptions import ConfigurationError

from palm_django._django_compat import is_migration_command


class PalmDjangoConfig(AppConfig):
    """Bootstrap Palm Engine when Django finishes loading apps."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "palm_django"
    verbose_name = "Palm Engine"

    def ready(self) -> None:
        from palm_django import checks  # noqa: F401
        from palm_django.providers import ensure_registered as ensure_provider_registered
        from palm_django.storages import ensure_registered as ensure_storage_registered

        ensure_storage_registered()
        ensure_provider_registered()

        from palm_django.admin import register_admin_models

        register_admin_models()

        if is_migration_command():
            return

        from palm_django.runtime import bootstrap_palm

        try:
            bootstrap_palm()
        except ConfigurationError as exc:
            if "storage tables are missing" not in str(exc):
                raise