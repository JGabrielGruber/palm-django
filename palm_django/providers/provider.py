"""
DjangoModelProvider — bridge Django ORM models to Palm's resource system.
"""

from __future__ import annotations

from typing import Any

from django.apps import apps
from django.db import models
from palm.core.resource.base_provider import BaseProvider
from palm.core.resource.result import (
    ProviderActionDescriptor,
    ProviderDescriptor,
    ProviderHealth,
    ProviderResult,
)

from palm_django.resources.registry import PROVIDER_NAME, get_palm_resource_config
from palm_django.resources.schema import schema_enabled, schema_options, validate_model_data
from palm_django.resources.serializer import serialize_instance
from palm_django.signals import emit_resource_invoked
from palm_django.transactions import django_atomic, palm_mutation

READ_ACTIONS = frozenset({"get", "list", "fetch"})
MUTATING_ACTIONS = frozenset({"create", "update", "delete"})
SUPPORTED_ACTIONS = READ_ACTIONS | MUTATING_ACTIONS


class DjangoModelProvider(BaseProvider):
    """Execute CRUD actions against Django ORM models."""

    def __init__(self, *, name: str = PROVIDER_NAME) -> None:
        super().__init__(name=name)
        self._connected = False

    def connect(self) -> None:
        if not apps.ready:
            raise RuntimeError("Django apps are not ready")
        self._connected = True

    def disconnect(self) -> None:
        self._connected = False

    def fetch(self, resource_id: str, **params: Any) -> Any:
        """Compatibility alias — treats ``resource_id`` as the lookup value."""
        merged = dict(params)
        lookup_field = str(merged.pop("lookup_field", "pk"))
        model = self._resolve_model(merged.pop("model", None))
        instance = model.objects.get(**{lookup_field: resource_id})
        fields = self._fields_param(merged)
        return serialize_instance(instance, fields=fields)

    def invoke(
        self,
        action: str,
        *,
        params: dict[str, Any] | None = None,
        resource_id: str | None = None,
        **kwargs: Any,
    ) -> ProviderResult:
        bound = dict(params or {})
        if resource_id is not None:
            bound.setdefault("resource_id", resource_id)

        normalized = "get" if action == "fetch" else action
        if normalized not in SUPPORTED_ACTIONS:
            return ProviderResult.fail(
                f"Unsupported action {action!r}",
                action=action,
                provider=self.name,
            )

        model_label = bound.get("model")
        if not model_label:
            return ProviderResult.fail(
                "Missing required param 'model'",
                action=normalized,
                provider=self.name,
            )

        try:
            model = self._resolve_model(str(model_label))
            lookup_field = str(bound.get("lookup_field", "pk"))
            fields = self._fields_param(bound)

            if normalized == "get":
                data = self._action_get(model, bound, lookup_field=lookup_field, fields=fields)
            elif normalized == "list":
                data = self._action_list(model, bound, fields=fields)
            elif normalized == "create":
                data = self._action_create(model, bound, fields=fields)
            elif normalized == "update":
                data = self._action_update(
                    model, bound, lookup_field=lookup_field, fields=fields
                )
            else:
                data = self._action_delete(model, bound, lookup_field=lookup_field)

            metadata: dict[str, Any] = {
                "action": normalized,
                "provider": self.name,
                "django_model": model._meta.label,
            }
            if normalized in {"get", "update", "delete"}:
                lookup_value = bound.get(lookup_field) or bound.get("resource_id")
                if lookup_value is not None:
                    metadata["resource_id"] = str(lookup_value)
            result = ProviderResult.ok(data, **metadata)
            emit_resource_invoked(
                provider=self.name,
                action=normalized,
                model_label=model._meta.label,
                params=bound,
                result=result,
            )
            return result
        except Exception as exc:
            return ProviderResult.fail(
                str(exc),
                action=normalized,
                provider=self.name,
            )

    def describe(self) -> ProviderDescriptor:
        return ProviderDescriptor(
            name=self.name,
            description="Django ORM model resource provider",
            actions=(
                ProviderActionDescriptor("get", "Retrieve a single model instance by lookup field"),
                ProviderActionDescriptor("list", "List instances with optional filters and ordering"),
                ProviderActionDescriptor("create", "Create a model instance from a data dict"),
                ProviderActionDescriptor("update", "Update a model instance by lookup field"),
                ProviderActionDescriptor("delete", "Delete a model instance by lookup field"),
                ProviderActionDescriptor("fetch", "Alias for get (Palm compatibility)"),
            ),
        )

    def health(self) -> ProviderHealth:
        if not self._connected:
            return ProviderHealth(healthy=False, message="not connected")
        return ProviderHealth(healthy=True, message="django orm ready")

    def _resolve_model(self, model_label: str | None) -> type[models.Model]:
        if not model_label:
            raise ValueError("Missing required param 'model'")
        model = apps.get_model(model_label)
        if model is None:
            raise LookupError(f"Unknown Django model {model_label!r}")
        return model

    @staticmethod
    def _fields_param(params: dict[str, Any]) -> tuple[str, ...] | None:
        raw = params.get("fields")
        if raw is None:
            return None
        if isinstance(raw, str):
            return (raw,)
        if isinstance(raw, list | tuple):
            return tuple(str(item) for item in raw)
        return None

    @staticmethod
    def _coerce_data(value: Any) -> dict[str, Any]:
        if not isinstance(value, dict):
            raise ValueError("Param 'data' must be a dict")
        return dict(value)

    @staticmethod
    def _lookup_value(params: dict[str, Any], lookup_field: str) -> Any:
        if lookup_field in params and params[lookup_field] not in (None, ""):
            return params[lookup_field]
        if "resource_id" in params and params["resource_id"] not in (None, ""):
            return params["resource_id"]
        raise ValueError(f"Missing lookup value for field {lookup_field!r}")

    def _action_get(
        self,
        model: type[models.Model],
        params: dict[str, Any],
        *,
        lookup_field: str,
        fields: tuple[str, ...] | None,
    ) -> dict[str, Any]:
        lookup_value = self._lookup_value(params, lookup_field)
        instance = model.objects.get(**{lookup_field: lookup_value})
        return serialize_instance(instance, fields=fields)

    def _action_list(
        self,
        model: type[models.Model],
        params: dict[str, Any],
        *,
        fields: tuple[str, ...] | None,
    ) -> list[dict[str, Any]]:
        queryset = model.objects.all()
        filters = params.get("filters")
        if isinstance(filters, dict) and filters:
            queryset = queryset.filter(**filters)

        order_by = params.get("order_by")
        if order_by not in (None, "", []):
            if isinstance(order_by, list | tuple):
                queryset = queryset.order_by(*[str(item) for item in order_by])
            else:
                queryset = queryset.order_by(str(order_by))

        limit = params.get("limit")
        if limit not in (None, ""):
            queryset = queryset[: int(limit)]

        return [serialize_instance(item, fields=fields) for item in queryset]

    def _validate_data_if_enabled(
        self,
        model: type[models.Model],
        data: dict[str, Any],
        *,
        for_create: bool,
    ) -> None:
        config = get_palm_resource_config(model)
        if config is None or not schema_enabled(config):
            return
        if not schema_options(config)["validate"]:
            return
        errors = validate_model_data(model, data, config, for_create=for_create)
        if errors:
            raise ValueError("; ".join(errors))

    def _action_create(
        self,
        model: type[models.Model],
        params: dict[str, Any],
        *,
        fields: tuple[str, ...] | None,
    ) -> dict[str, Any]:
        data = self._coerce_data(params.get("data", {}))
        self._validate_data_if_enabled(model, data, for_create=True)
        with palm_mutation(), django_atomic():
            instance = model.objects.create(**data)
        return serialize_instance(instance, fields=fields)

    def _action_update(
        self,
        model: type[models.Model],
        params: dict[str, Any],
        *,
        lookup_field: str,
        fields: tuple[str, ...] | None,
    ) -> dict[str, Any]:
        lookup_value = self._lookup_value(params, lookup_field)
        data = self._coerce_data(params.get("data", {}))
        self._validate_data_if_enabled(model, data, for_create=False)
        with palm_mutation(), django_atomic():
            instance = model.objects.get(**{lookup_field: lookup_value})
            for key, value in data.items():
                setattr(instance, key, value)
            instance.save(update_fields=list(data.keys()) if data else None)
        return serialize_instance(instance, fields=fields)

    def _action_delete(
        self,
        model: type[models.Model],
        params: dict[str, Any],
        *,
        lookup_field: str,
    ) -> dict[str, Any]:
        lookup_value = self._lookup_value(params, lookup_field)
        with palm_mutation(), django_atomic():
            deleted, _details = model.objects.filter(**{lookup_field: lookup_value}).delete()
        return {"deleted": deleted, lookup_field: lookup_value, "model": model._meta.label}