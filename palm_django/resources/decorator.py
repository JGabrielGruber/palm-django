"""
Decorator and Meta options for exposing Django models as Palm resources.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from typing import Any, TypeVar

from palm_django.resources.config import DEFAULT_ACTIONS, PalmResourceConfig

_ModelT = TypeVar("_ModelT", bound=type)

PALM_RESOURCE_ATTR = "_palm_resource_config"


def as_palm_resource(
    cls: _ModelT | None = None,
    *,
    actions: Sequence[str] | None = None,
    lookup_field: str = "pk",
    output_key: str | None = None,
    name_prefix: str | None = None,
    fields: Sequence[str] | None = None,
    extra_params: dict[str, Any] | None = None,
    schema: bool | dict[str, Any] | None = None,
) -> Callable[[_ModelT], _ModelT] | _ModelT:
    """
    Mark a Django model for auto-registration as Palm resources.

    Usage::

        @as_palm_resource(actions=["get", "create", "list"], schema=True)
        class Order(models.Model):
            ...
    """

    def decorate(model_cls: _ModelT) -> _ModelT:
        config = PalmResourceConfig(
            actions=tuple(actions or DEFAULT_ACTIONS),
            lookup_field=lookup_field,
            output_key=output_key,
            name_prefix=name_prefix,
            fields=tuple(fields) if fields else None,
            extra_params=dict(extra_params or {}),
            schema=schema,
        )
        setattr(model_cls, PALM_RESOURCE_ATTR, config)
        return model_cls

    if cls is not None:
        return decorate(cls)
    return decorate