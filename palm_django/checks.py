"""
Django system checks for Palm integration health.
"""

from __future__ import annotations

from django.core.checks import Error, Tags, register

from palm_django.runtime import get_runtime, is_palm_started


@register(Tags.compatibility)
def check_palm_runtime_started(**_kwargs: object) -> list[Error]:
    issues: list[Error] = []
    if not is_palm_started():
        issues.append(
            Error(
                "Palm ApplicationHost is not started.",
                hint="Set PALM_AUTO_START = True (default) or call palm_django.bootstrap_palm().",
                id="palm_django.E001",
            )
        )
    return issues


@register(Tags.compatibility)
def check_palm_discovery_errors(**_kwargs: object) -> list[Error]:
    runtime = get_runtime()
    discovery = runtime.discovery
    if discovery is None:
        return []

    return [
        Error(
            f"Palm discovery failed for {message}",
            id="palm_django.E002",
        )
        for message in discovery.errors
    ]