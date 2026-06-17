"""
Configuration for Django models exposed as Palm resources.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

DEFAULT_ACTIONS: tuple[str, ...] = ("get", "create", "update", "delete", "list")


@dataclass(frozen=True)
class PalmResourceConfig:
    """How a Django model is exposed through Palm resources."""

    actions: tuple[str, ...] = DEFAULT_ACTIONS
    lookup_field: str = "pk"
    output_key: str | None = None
    name_prefix: str | None = None
    fields: tuple[str, ...] | None = None
    extra_params: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_options(cls, options: Any) -> PalmResourceConfig:
        if isinstance(options, cls):
            return options
        if isinstance(options, dict):
            return cls(**{k: v for k, v in options.items() if k in cls.__dataclass_fields__})
        actions = getattr(options, "actions", None) or DEFAULT_ACTIONS
        return cls(
            actions=tuple(str(item) for item in actions),
            lookup_field=str(getattr(options, "lookup_field", "pk")),
            output_key=getattr(options, "output_key", None),
            name_prefix=getattr(options, "name_prefix", None),
            fields=(
                tuple(str(item) for item in options.fields)
                if getattr(options, "fields", None)
                else None
            ),
            extra_params=dict(getattr(options, "extra_params", {}) or {}),
        )

    def normalized_actions(self) -> tuple[str, ...]:
        allowed = set(DEFAULT_ACTIONS)
        return tuple(action for action in self.actions if action in allowed)