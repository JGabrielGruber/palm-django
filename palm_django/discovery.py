"""
Auto-discovery of Palm integration hooks from Django installed apps.
"""

from __future__ import annotations

import importlib
from dataclasses import dataclass, field
from typing import Any

from django.apps import apps
from palm.common.persistence.definition_repository import DefinitionRepository


@dataclass
class DiscoveryReport:
    """Summary of Palm hooks discovered across Django apps."""

    apps_scanned: int = 0
    definition_modules: list[str] = field(default_factory=list)
    resource_modules: list[str] = field(default_factory=list)
    commit_handler_modules: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    @property
    def modules_loaded(self) -> list[str]:
        seen: set[str] = set()
        ordered: list[str] = []
        for name in (
            *self.definition_modules,
            *self.resource_modules,
            *self.commit_handler_modules,
        ):
            if name not in seen:
                seen.add(name)
                ordered.append(name)
        return ordered


def _import_app_module(app_config: Any, module_suffix: str) -> Any | None:
    module_name = f"{app_config.name}.{module_suffix}"
    try:
        return importlib.import_module(module_name)
    except ModuleNotFoundError:
        return None


def _call_hook(module: Any, hook_name: str, *args: Any, **kwargs: Any) -> bool:
    hook = getattr(module, hook_name, None)
    if not callable(hook):
        return False
    hook(*args, **kwargs)
    return True


def discover_and_register(
    repository: DefinitionRepository,
    *,
    discovery_modules: tuple[str, ...] = ("palm_definitions", "palm"),
    discover_definitions: bool = True,
    discover_resources: bool = True,
    discover_commit_handlers: bool = True,
) -> DiscoveryReport:
    """
    Import Palm hook modules from each installed Django app and invoke registrars.

    Convention (per app)::

        myapp/palm_definitions.py   # register_definitions(repository)
        myapp/palm.py               # optional alternate module name
    """
    report = DiscoveryReport()
    for app_config in apps.get_app_configs():
        report.apps_scanned += 1
        for module_suffix in discovery_modules:
            module = _import_app_module(app_config, module_suffix)
            if module is None:
                continue

            module_name = module.__name__
            try:
                if discover_definitions and _call_hook(module, "register_definitions", repository):
                    report.definition_modules.append(module_name)

                if discover_resources and _call_hook(module, "register_resources", repository):
                    report.resource_modules.append(module_name)

                if discover_commit_handlers and _call_hook(
                    module, "register_commit_handlers", repository
                ):
                    report.commit_handler_modules.append(module_name)
            except Exception as exc:
                report.errors.append(f"{module_name}: {exc}")

    return report


def find_discoverable_modules(
    *,
    discovery_modules: tuple[str, ...] = ("palm_definitions", "palm"),
) -> list[str]:
    """Return import paths for discoverable Palm modules (imports each candidate)."""
    found: list[str] = []
    for app_config in apps.get_app_configs():
        for module_suffix in discovery_modules:
            module_name = f"{app_config.name}.{module_suffix}"
            try:
                importlib.import_module(module_name)
            except ModuleNotFoundError:
                continue
            found.append(module_name)
    return found