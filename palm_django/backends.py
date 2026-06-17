"""
Django ORM storage backend for Palm Engine.
"""

from __future__ import annotations

import logging
import threading
from typing import Any

from django.db import connection
from palm.core.exceptions import ConfigurationError
from palm.core.storage import BaseBackend

from palm_django.models import PalmDefinition, PalmProcessInstance, PalmStorageEntry
from palm_django.storage_keys import namespace_for_key, parse_storage_key
from palm_django.transactions import django_atomic

logger = logging.getLogger(__name__)

class DjangoStorageBackend(BaseBackend):
    """
    Durable Palm storage backed by Django ORM.

    Definition and instance keys map to structured models; indexes, projections,
    outbox entries, and other keys use :class:`~palm_django.models.PalmStorageEntry`.
    All operations run inside :func:`django.db.transaction.atomic` so callers can
    compose Palm writes with surrounding Django transactions.
    """

    def __init__(self, *, name: str = "django") -> None:
        super().__init__(name=name)
        self._lock = threading.RLock()

    def open(self) -> None:
        if self._is_open:
            return
        self._ensure_tables()
        self._is_open = True

    def get(self, key: str) -> Any | None:
        self.ensure_open()
        with self._lock:
            with django_atomic():
                return self._get_unlocked(key)

    def set(self, key: str, value: Any) -> None:
        self.ensure_open()
        with self._lock:
            with django_atomic():
                self._set_unlocked(key, value)

    def delete(self, key: str) -> None:
        self.ensure_open()
        with self._lock:
            with django_atomic():
                self._delete_unlocked(key)

    def close(self) -> None:
        self._is_open = False

    def _get_unlocked(self, key: str) -> Any | None:
        parsed = parse_storage_key(key)
        if parsed.route == "definition":
            row = (
                PalmDefinition.objects.filter(
                    kind=parsed.definition_kind,
                    definition_id=parsed.entity_id,
                )
                .values_list("data", flat=True)
                .first()
            )
            return row
        if parsed.route == "instance":
            row = (
                PalmProcessInstance.objects.filter(instance_id=parsed.entity_id)
                .values_list("data", flat=True)
                .first()
            )
            return row
        row = PalmStorageEntry.objects.filter(key=key).values_list("value", flat=True).first()
        return row

    def _set_unlocked(self, key: str, value: Any) -> None:
        parsed = parse_storage_key(key)
        if parsed.route == "definition":
            if not isinstance(value, dict):
                raise ConfigurationError(
                    f"Definition storage value for {key!r} must be a dict, got {type(value)!r}"
                )
            PalmDefinition.objects.update_or_create(
                kind=parsed.definition_kind,
                definition_id=parsed.entity_id,
                defaults={
                    "name": str(value.get("name", "")),
                    "data": value,
                },
            )
            return
        if parsed.route == "instance":
            if not isinstance(value, dict):
                raise ConfigurationError(
                    f"Instance storage value for {key!r} must be a dict, got {type(value)!r}"
                )
            PalmProcessInstance.objects.update_or_create(
                instance_id=parsed.entity_id,
                defaults={
                    "job_id": str(value.get("job_id", "")),
                    "status": str(value.get("status", "")),
                    "data": value,
                },
            )
            return
        PalmStorageEntry.objects.update_or_create(
            key=key,
            defaults={
                "namespace": namespace_for_key(key),
                "value": value,
            },
        )

    def _delete_unlocked(self, key: str) -> None:
        parsed = parse_storage_key(key)
        if parsed.route == "definition":
            PalmDefinition.objects.filter(
                kind=parsed.definition_kind,
                definition_id=parsed.entity_id,
            ).delete()
            return
        if parsed.route == "instance":
            PalmProcessInstance.objects.filter(instance_id=parsed.entity_id).delete()
            return
        PalmStorageEntry.objects.filter(key=key).delete()

    def _ensure_tables(self) -> None:
        required = {
            PalmDefinition._meta.db_table,
            PalmProcessInstance._meta.db_table,
            PalmStorageEntry._meta.db_table,
        }
        existing = set(connection.introspection.table_names())
        missing = sorted(required - existing)
        if missing:
            raise ConfigurationError(
                "Django ORM storage tables are missing: "
                f"{', '.join(missing)}. Run: python manage.py migrate palm_django"
            )


def storage_health_report() -> dict[str, Any]:
    """Return model counts and table readiness for doctor / system checks."""
    required = {
        PalmDefinition._meta.db_table,
        PalmProcessInstance._meta.db_table,
        PalmStorageEntry._meta.db_table,
    }
    existing = set(connection.introspection.table_names())
    missing = sorted(required - existing)
    ready = not missing

    counts: dict[str, int | None] = {
        "definitions": None,
        "instances": None,
        "kv_entries": None,
    }
    if ready:
        counts["definitions"] = PalmDefinition.objects.count()
        counts["instances"] = PalmProcessInstance.objects.count()
        counts["kv_entries"] = PalmStorageEntry.objects.count()

    return {
        "backend": "django",
        "tables_ready": ready,
        "missing_tables": missing,
        "counts": counts,
    }