"""
Serialize Django model instances for Palm provider results.
"""

from __future__ import annotations

from datetime import date, datetime, time
from decimal import Decimal
from typing import Any
from uuid import UUID

from django.db import models


def serialize_instance(
    instance: models.Model,
    *,
    fields: tuple[str, ...] | None = None,
) -> dict[str, Any]:
    """Convert a model instance to a JSON-friendly dict."""
    payload: dict[str, Any] = {}
    allowed = set(fields) if fields else None
    for field in instance._meta.concrete_fields:
        if allowed is not None and field.name not in allowed:
            continue
        value = field.value_from_object(instance)
        payload[field.name] = _json_safe(value)
    return payload


def _json_safe(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, str | int | float | bool):
        return value
    if isinstance(value, datetime | date | time):
        return value.isoformat()
    if isinstance(value, Decimal | UUID):
        return str(value)
    if isinstance(value, models.Model):
        return value.pk
    return str(value)