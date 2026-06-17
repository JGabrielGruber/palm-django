"""
Django signals for Palm resource and model lifecycle events.
"""

from __future__ import annotations

from typing import Any

from django.db import models
from django.dispatch import Signal
from palm.core.resource.result import ProviderResult

# Fired after a Palm provider successfully invokes an action.
# kwargs: provider, action, model_label, params, result
palm_resource_invoked = Signal()

# Fired when a decorated Django model is saved via the ORM (not via Palm provider).
# kwargs: instance, created, model_label
palm_model_saved = Signal()


def emit_resource_invoked(
    *,
    provider: str,
    action: str,
    model_label: str,
    params: dict[str, Any],
    result: ProviderResult,
) -> None:
    palm_resource_invoked.send(
        sender=None,
        provider=provider,
        action=action,
        model_label=model_label,
        params=params,
        result=result,
    )


def connect_model_save_signals() -> None:
    """Connect ``post_save`` receivers for models exposed as Palm resources."""
    for model in _iter_resource_models():
        models.signals.post_save.connect(
            _on_decorated_model_saved,
            sender=model,
            dispatch_uid=f"palm_django.model_saved.{model._meta.label}",
            weak=False,
        )


def _iter_resource_models() -> list[type[models.Model]]:
    from django.apps import apps

    from palm_django.resources.registry import get_palm_resource_config

    found: list[type[models.Model]] = []
    for model in apps.get_models():
        if model._meta.abstract or model._meta.auto_created:
            continue
        if get_palm_resource_config(model) is not None:
            found.append(model)
    return found


def _on_decorated_model_saved(
    sender: type[models.Model],
    instance: models.Model,
    created: bool,
    **kwargs: Any,
) -> None:
    from palm_django.transactions import in_palm_mutation

    if in_palm_mutation():
        return
    palm_model_saved.send(
        sender=sender,
        instance=instance,
        created=created,
        model_label=sender._meta.label,
    )