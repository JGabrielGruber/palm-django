"""
Django model → Palm resource registration.
"""

from palm_django.resources.decorator import as_palm_resource
from palm_django.resources.registry import (
    build_resource_definitions,
    get_palm_resource_config,
    list_registered_models,
    register_discovered_model_resources,
)
from palm_django.resources.schema import (
    model_data_schema_name,
    model_fields_schema_dict,
    model_instance_schema_name,
    model_to_dict_state_schema,
    schema_enabled,
)

__all__ = [
    "as_palm_resource",
    "build_resource_definitions",
    "get_palm_resource_config",
    "list_registered_models",
    "model_data_schema_name",
    "model_fields_schema_dict",
    "model_instance_schema_name",
    "model_to_dict_state_schema",
    "register_discovered_model_resources",
    "schema_enabled",
]