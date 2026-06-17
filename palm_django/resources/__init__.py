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

__all__ = [
    "as_palm_resource",
    "build_resource_definitions",
    "get_palm_resource_config",
    "list_registered_models",
    "register_discovered_model_resources",
]