"""
Django ↔ Palm settings bridge.

Reads ``PALM`` dict and ``PALM_*`` attributes from Django ``settings`` and
builds a :class:`~palm.app.settings.PalmSettings` instance.
"""

from __future__ import annotations

from typing import Any

from django.conf import settings as django_settings
from palm.app.settings import PalmSettings

# Keys managed by palm-django itself — not forwarded to PalmSettings.
_DJANGO_ONLY_KEYS = frozenset(
    {
        "AUTO_START",
        "DISCOVERY_MODULES",
        "DISCOVER_DEFINITIONS",
        "DISCOVER_RESOURCES",
        "DISCOVER_COMMIT_HANDLERS",
    }
)

# Django settings attribute names owned by palm-django integration.
_DJANGO_SETTING_NAMES = frozenset(
    {
        "PALM",
        "PALM_AUTO_START",
        "PALM_DISCOVERY_MODULES",
        "PALM_DISCOVER_DEFINITIONS",
        "PALM_DISCOVER_RESOURCES",
        "PALM_DISCOVER_COMMIT_HANDLERS",
    }
)

DEFAULT_PALM_SETTINGS: dict[str, Any] = {
    "load_example_definitions": False,
    "storage_backend": "memory",
    "host_profile": "all_in_one",
    "default_scheduler": "inline",
    "rebuild_projections_on_startup": False,
    "enable_compensation": False,
    "enable_outbox_service": False,
}

DEFAULT_DISCOVERY_MODULES: tuple[str, ...] = ("palm_definitions", "palm")


def _normalize_key(key: str) -> str:
    return key.removeprefix("PALM_").lower()


def _coerce_value(key: str, value: Any) -> Any:
    if value is None:
        return None
    if key == "data_dir" and isinstance(value, str):
        from pathlib import Path

        return Path(value)
    if key in {"auth_roles", "host_roles", "snapshot_on_status", "webhook_urls", "webhook_event_types"}:
        if isinstance(value, str):
            return [item.strip() for item in value.split(",") if item.strip()]
    return value


def _extract_palm_dict() -> dict[str, Any]:
    raw = getattr(django_settings, "PALM", None)
    if raw is None:
        return {}
    if not isinstance(raw, dict):
        raise TypeError("PALM setting must be a dict")
    normalized: dict[str, Any] = {}
    for key, value in raw.items():
        normalized_key = _normalize_key(str(key))
        if normalized_key in _DJANGO_ONLY_KEYS:
            continue
        normalized[normalized_key] = _coerce_value(normalized_key, value)
    return normalized


def _extract_prefixed_settings() -> dict[str, Any]:
    extracted: dict[str, Any] = {}
    for name in dir(django_settings):
        if not name.startswith("PALM_") or name in _DJANGO_SETTING_NAMES:
            continue
        key = _normalize_key(name)
        if key in _DJANGO_ONLY_KEYS:
            continue
        extracted[key] = _coerce_value(key, getattr(django_settings, name))
    return extracted


def build_palm_settings_dict() -> dict[str, Any]:
    """Merge defaults, ``PALM`` dict, and individual ``PALM_*`` Django settings."""
    merged = dict(DEFAULT_PALM_SETTINGS)
    merged.update(_extract_palm_dict())
    merged.update(_extract_prefixed_settings())
    return merged


def get_palm_settings() -> PalmSettings:
    """Return PalmSettings configured from the active Django settings module."""
    return PalmSettings(**build_palm_settings_dict())


def get_django_integration_settings() -> dict[str, Any]:
    """Return palm-django-specific options from Django settings."""
    palm_dict = getattr(django_settings, "PALM", {}) or {}
    if not isinstance(palm_dict, dict):
        raise TypeError("PALM setting must be a dict")

    def _resolve(name: str, default: Any) -> Any:
        upper = name.upper()
        lower = name.lower()
        if upper in palm_dict:
            return palm_dict[upper]
        if lower in palm_dict:
            return palm_dict[lower]
        attr = f"PALM_{upper}"
        if hasattr(django_settings, attr):
            return getattr(django_settings, attr)
        return default

    discovery_modules = _resolve("discovery_modules", DEFAULT_DISCOVERY_MODULES)
    if isinstance(discovery_modules, str):
        discovery_modules = tuple(
            item.strip() for item in discovery_modules.split(",") if item.strip()
        )
    elif isinstance(discovery_modules, list | tuple):
        discovery_modules = tuple(str(item) for item in discovery_modules)
    else:
        discovery_modules = DEFAULT_DISCOVERY_MODULES

    return {
        "auto_start": bool(_resolve("auto_start", True)),
        "discovery_modules": discovery_modules,
        "discover_definitions": bool(_resolve("discover_definitions", True)),
        "discover_resources": bool(_resolve("discover_resources", True)),
        "discover_commit_handlers": bool(_resolve("discover_commit_handlers", True)),
    }