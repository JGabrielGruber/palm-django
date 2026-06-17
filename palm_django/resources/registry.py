"""
Build and register Palm ResourceDefinitions from decorated Django models.
"""

from __future__ import annotations

from typing import Any

from django.apps import apps
from django.db import models
from palm.common.persistence.definition_repository import DefinitionRepository
from palm.definitions.resource import ResourceDefinition

from palm_django.resources.config import PalmResourceConfig
from palm_django.resources.decorator import PALM_RESOURCE_ATTR

PROVIDER_NAME = "django_model"


def get_palm_resource_config(model: type[models.Model]) -> PalmResourceConfig | None:
    """Return Palm resource config from decorator or class-level ``palm_resource``."""
    direct = getattr(model, PALM_RESOURCE_ATTR, None)
    if direct is not None:
        return PalmResourceConfig.from_options(direct)

    class_option = getattr(model, "palm_resource", None)
    if class_option is not None:
        return PalmResourceConfig.from_options(class_option)
    return None


def resource_name(model: type[models.Model], action: str, *, config: PalmResourceConfig) -> str:
    prefix = config.name_prefix or model._meta.label_lower
    return f"{prefix}.{action}"


def build_resource_definitions(
    model: type[models.Model],
    config: PalmResourceConfig,
) -> list[ResourceDefinition]:
    """Create one ResourceDefinition per configured action."""
    model_label = model._meta.label
    lookup = config.lookup_field
    output_key = config.output_key or model._meta.model_name
    base_params: dict[str, Any] = {"model": model_label, **config.extra_params}
    definitions: list[ResourceDefinition] = []

    for action in config.normalized_actions():
        params = dict(base_params)
        metadata = {
            "django_model": model_label,
            "django_action": action,
            "lookup_field": lookup,
        }
        if config.fields:
            metadata["fields"] = list(config.fields)

        if action == "get":
            params[lookup] = f"{{{{ state.{lookup} }}}}"
        elif action == "list":
            params.setdefault("filters", "{{ state.filters }}")
            params.setdefault("order_by", "{{ state.order_by }}")
            params.setdefault("limit", "{{ state.limit }}")
        elif action == "create":
            params["data"] = "{{ state.data }}"
        elif action == "update":
            params[lookup] = f"{{{{ state.{lookup} }}}}"
            params["data"] = "{{ state.data }}"
        elif action == "delete":
            params[lookup] = f"{{{{ state.{lookup} }}}}"

        definitions.append(
            ResourceDefinition(
                id=f"resource-{resource_name(model, action, config=config)}",
                name=resource_name(model, action, config=config),
                provider=PROVIDER_NAME,
                action=action,
                params=params,
                output_key=output_key,
                metadata=metadata,
            )
        )
    return definitions


def register_discovered_model_resources(repository: DefinitionRepository) -> list[str]:
    """Scan installed models and register Palm resources for decorated models."""
    registered: list[str] = []
    for model in apps.get_models():
        if model._meta.abstract or model._meta.auto_created:
            continue
        config = get_palm_resource_config(model)
        if config is None:
            continue
        for resource in build_resource_definitions(model, config):
            repository.register_resource(resource)
            registered.append(resource.name)
    return registered


def list_registered_models() -> list[tuple[str, PalmResourceConfig]]:
    """Return ``(model_label, config)`` pairs for models with Palm resource config."""
    found: list[tuple[str, PalmResourceConfig]] = []
    for model in apps.get_models():
        if model._meta.abstract or model._meta.auto_created:
            continue
        config = get_palm_resource_config(model)
        if config is None:
            continue
        found.append((model._meta.label, config))
    return found