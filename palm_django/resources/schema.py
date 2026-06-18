"""
Generate Palm ``DictStateSchema`` documents from Django model fields.
"""

from __future__ import annotations

from typing import Any

from django.db import models
from palm.core.context import DictStateSchema
from palm.definitions.schema import StateSchemaDefinition

from palm_django.resources.config import PalmResourceConfig

SCHEMA_OPTIONS_DEFAULT: dict[str, bool] = {
    "register": True,
    "input": True,
    "output": True,
    "validate": True,
}


def schema_enabled(config: PalmResourceConfig) -> bool:
    """Return whether schema generation is enabled for a resource config."""
    return _normalized_schema_options(config) is not None


def schema_options(config: PalmResourceConfig) -> dict[str, bool]:
    """Return normalized schema feature flags."""
    return _normalized_schema_options(config) or dict(SCHEMA_OPTIONS_DEFAULT)


def _normalized_schema_options(config: PalmResourceConfig) -> dict[str, bool] | None:
    raw = config.schema
    if not raw:
        return None
    if raw is True:
        return dict(SCHEMA_OPTIONS_DEFAULT)
    if isinstance(raw, dict):
        merged = dict(SCHEMA_OPTIONS_DEFAULT)
        merged.update({str(k): bool(v) for k, v in raw.items()})
        return merged
    return None


def model_schema_prefix(model: type[models.Model], config: PalmResourceConfig) -> str:
    return config.name_prefix or model._meta.label_lower


def model_data_schema_name(model: type[models.Model], config: PalmResourceConfig) -> str:
    return f"{model_schema_prefix(model, config)}.data"


def model_instance_schema_name(model: type[models.Model], config: PalmResourceConfig) -> str:
    return f"{model_schema_prefix(model, config)}.instance"


def model_to_dict_state_schema(
    model: type[models.Model],
    config: PalmResourceConfig | None = None,
    *,
    writable_only: bool = False,
) -> DictStateSchema:
    """Materialize a :class:`~palm.core.context.DictStateSchema` for model fields."""
    cfg = config or PalmResourceConfig()
    return DictStateSchema(model_fields_schema_dict(model, cfg, writable_only=writable_only))


def model_fields_schema_dict(
    model: type[models.Model],
    config: PalmResourceConfig,
    *,
    writable_only: bool = False,
    for_create: bool = False,
) -> dict[str, Any]:
    """Build a JSON-schema-style object document for a Django model."""
    properties: dict[str, Any] = {}
    required: list[str] = []

    for field in _iter_model_fields(model, config):
        if writable_only and not _is_writable_field(field, for_create=for_create):
            continue
        properties[field.name] = django_field_to_schema(field)
        if writable_only and _is_required_field(field, for_create=for_create):
            required.append(field.name)

    payload: dict[str, Any] = {"type": "object", "properties": properties}
    if required:
        payload["required"] = required
    return payload


def django_field_to_schema(field: models.Field[Any, Any]) -> dict[str, Any]:
    """Map a Django model field to a Palm schema property spec."""
    spec: dict[str, Any] = {"type": _field_type(field)}

    if isinstance(field, models.CharField | models.TextField | models.SlugField):
        if field.max_length is not None:
            spec["maxLength"] = field.max_length

    if isinstance(field, models.DecimalField):
        if field.max_digits is not None:
            spec["maximum"] = int("9" * field.max_digits)

    choices = _field_choices(field)
    if choices:
        spec["enum"] = choices

    if getattr(field, "null", False) or getattr(field, "blank", False):
        spec["type"] = [spec["type"], "null"]

    if field.has_default() and not callable(field.default):
        spec["default"] = field.default

    return spec


def build_action_input_schema(
    model: type[models.Model],
    action: str,
    config: PalmResourceConfig,
) -> dict[str, Any] | None:
    """Return an input schema for a model resource action."""
    if not schema_enabled(config) or not schema_options(config)["input"]:
        return None

    lookup = config.lookup_field
    lookup_spec = django_field_to_schema(_resolve_lookup_field(model, lookup))

    if action == "create":
        return {
            "type": "object",
            "properties": {
                "data": model_fields_schema_dict(
                    model,
                    config,
                    writable_only=True,
                    for_create=True,
                ),
            },
            "required": ["data"],
        }

    if action == "update":
        data_schema = model_fields_schema_dict(
            model,
            config,
            writable_only=True,
            for_create=False,
        )
        data_schema.pop("required", None)
        return {
            "type": "object",
            "properties": {
                lookup: lookup_spec,
                "data": data_schema,
            },
            "required": [lookup],
        }

    if action in {"get", "delete"}:
        return {
            "type": "object",
            "properties": {lookup: lookup_spec},
            "required": [lookup],
        }

    if action == "list":
        return {
            "type": "object",
            "properties": {
                "filters": {"type": "object"},
                "order_by": {"type": ["string", "array", "null"]},
                "limit": {"type": ["integer", "null"]},
            },
        }

    return None


def build_action_output_schema(
    model: type[models.Model],
    action: str,
    config: PalmResourceConfig,
) -> dict[str, Any] | None:
    """Return an output schema for a model resource action."""
    if not schema_enabled(config) or not schema_options(config)["output"]:
        return None

    instance_schema = model_fields_schema_dict(model, config, writable_only=False)

    if action == "list":
        return {"type": "array", "items": instance_schema}

    if action == "delete":
        lookup = config.lookup_field
        return {
            "type": "object",
            "properties": {
                "deleted": {"type": "integer"},
                lookup: django_field_to_schema(_resolve_lookup_field(model, lookup)),
                "model": {"type": "string"},
            },
        }

    if action in {"get", "create", "update"}:
        return instance_schema

    return None


def build_state_schema_definitions(
    model: type[models.Model],
    config: PalmResourceConfig,
) -> list[StateSchemaDefinition]:
    """Build reusable state schema definitions for wizard and flow binding."""
    if not schema_enabled(config) or not schema_options(config)["register"]:
        return []

    prefix = model_schema_prefix(model, config)
    model_label = model._meta.label
    return [
        StateSchemaDefinition(
            id=f"schema-{prefix}-data",
            name=model_data_schema_name(model, config),
            schema=model_fields_schema_dict(
                model,
                config,
                writable_only=True,
                for_create=True,
            ),
            metadata={
                "django_model": model_label,
                "django_schema_kind": "data",
            },
        ),
        StateSchemaDefinition(
            id=f"schema-{prefix}-instance",
            name=model_instance_schema_name(model, config),
            schema=model_fields_schema_dict(model, config, writable_only=False),
            metadata={
                "django_model": model_label,
                "django_schema_kind": "instance",
            },
        ),
    ]


def validate_model_data(
    model: type[models.Model],
    data: Any,
    config: PalmResourceConfig,
    *,
    for_create: bool = True,
) -> list[str]:
    """Validate a data payload against the generated model data schema."""
    if not isinstance(data, dict):
        return ["data: expected object"]
    schema = DictStateSchema(
        model_fields_schema_dict(
            model,
            config,
            writable_only=True,
            for_create=for_create,
        )
    )
    return schema.validate_state(data)


def register_model_schemas(
    repository: Any,
    model: type[models.Model],
    config: PalmResourceConfig,
) -> list[str]:
    """Register state schema definitions for a model."""
    registered: list[str] = []
    for schema in build_state_schema_definitions(model, config):
        repository.register_schema(schema)
        registered.append(schema.name)
    return registered


def _iter_model_fields(
    model: type[models.Model],
    config: PalmResourceConfig,
) -> list[models.Field[Any, Any]]:
    allowed = set(config.fields) if config.fields else None
    fields: list[models.Field[Any, Any]] = []
    for field in model._meta.concrete_fields:
        if allowed is not None and field.name not in allowed:
            continue
        fields.append(field)
    return fields


def _is_writable_field(field: models.Field[Any, Any], *, for_create: bool) -> bool:
    if isinstance(field, models.AutoField | models.BigAutoField):
        return False
    if not field.editable:
        return False
    if for_create and field.primary_key:
        return False
    return True


def _is_required_field(field: models.Field[Any, Any], *, for_create: bool) -> bool:
    if not _is_writable_field(field, for_create=for_create):
        return False
    if getattr(field, "null", False):
        return False
    if getattr(field, "blank", False):
        return False
    if field.has_default():
        return False
    if for_create and isinstance(field, models.AutoField | models.BigAutoField):
        return False
    return True


def _field_type(field: models.Field[Any, Any]) -> str:
    if isinstance(field, models.BooleanField):
        return "boolean"
    if isinstance(field, models.IntegerField | models.BigIntegerField | models.SmallIntegerField):
        return "integer"
    if isinstance(field, models.FloatField | models.DecimalField):
        return "number"
    if isinstance(field, models.JSONField):
        return "object"
    return "string"


def _resolve_lookup_field(model: type[models.Model], lookup: str) -> models.Field[Any, Any]:
    if lookup == "pk":
        return model._meta.pk
    return model._meta.get_field(lookup)


def _field_choices(field: models.Field[Any, Any]) -> list[Any] | None:
    choices = getattr(field, "choices", None)
    if not choices:
        return None
    return [choice[0] for choice in choices]