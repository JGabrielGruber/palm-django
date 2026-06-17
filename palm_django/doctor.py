"""
Health report builder for ``python manage.py palm doctor``.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from django.db import connection

from palm_django.backends import storage_health_report
from palm_django.resources.registry import PROVIDER_NAME, list_registered_models
from palm_django.runtime import get_app, get_host, get_runtime, is_palm_started
from palm_django.settings import build_palm_settings_dict, get_django_integration_settings


@dataclass
class DoctorReport:
    """Structured Palm x Django health report."""

    issues: list[str] = field(default_factory=list)
    tips: list[str] = field(default_factory=list)
    sections: list[tuple[str, list[tuple[str, Any]]]] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.issues


def build_doctor_report(*, django_version: str) -> DoctorReport:
    """Collect integration health data for human or machine-readable output."""
    from palm import __version__ as palm_version

    from palm_django import __version__ as palm_django_version

    report = DoctorReport()

    if not is_palm_started():
        from palm_django.runtime import bootstrap_palm

        bootstrap_palm()
    if not is_palm_started():
        report.issues.append("ApplicationHost is not started")

    host = get_host()
    app = get_app()
    runtime = get_runtime()
    integration = get_django_integration_settings()
    palm_config = build_palm_settings_dict()

    storage = app.storage
    backend_name = storage.backend_name or "(none)"
    backend_open = storage.backend is not None and storage.backend.is_open
    if not backend_open:
        report.issues.append(f"Storage backend {backend_name!r} is not open")

    db = connection.settings_dict
    db_line = f"{connection.vendor} / {db.get('NAME', '(unknown)')}"

    report.sections.append(
        (
            "Versions",
            [
                ("palm-django", palm_django_version),
                ("palmengine", palm_version),
                ("django", django_version),
                ("database", db_line),
            ],
        )
    )

    report.sections.append(
        (
            "Runtime",
            [
                ("host started", "yes" if host.is_started else "no"),
                ("host roles", ", ".join(sorted(host.profile.roles))),
                ("running runtimes", ", ".join(app.running()) or "(none)"),
                ("primary runtime", app.primary_name or "(none)"),
                ("storage backend", backend_name),
                ("storage open", "yes" if backend_open else "no"),
                ("storage durable", "yes" if backend_name == "django" else "no"),
                ("transaction bridging", "django_atomic uses savepoints when nested"),
            ],
        )
    )

    storage_report = storage_health_report()
    storage_rows: list[tuple[str, Any]] = [
        ("tables ready", "yes" if storage_report["tables_ready"] else "no"),
    ]
    if storage_report["missing_tables"]:
        for table in storage_report["missing_tables"]:
            report.issues.append(f"missing storage table: {table}")
        storage_rows.append(("missing tables", ", ".join(storage_report["missing_tables"])))
    counts = storage_report["counts"]
    if counts["definitions"] is not None:
        storage_rows.extend(
            [
                ("orm definition rows", counts["definitions"]),
                ("orm instance rows", counts["instances"]),
                ("orm kv rows", counts["kv_entries"]),
            ]
        )
    report.sections.append(("Django ORM Storage", storage_rows))

    report.sections.append(
        (
            "Operator Tools",
            [
                (
                    "management commands",
                    "doctor, quickstart, server, host server, run, flow, instance, resource",
                ),
                ("server mode", "python manage.py palm server (Palm Explorer)"),
                ("django admin", _admin_status()),
            ],
        )
    )

    report.sections.append(
        (
            "Django Integration",
            [
                ("auto_start", integration["auto_start"]),
                ("discovery modules", ", ".join(integration["discovery_modules"])),
                ("discover definitions", integration["discover_definitions"]),
                ("discover resources", integration["discover_resources"]),
                ("discover commit handlers", integration["discover_commit_handlers"]),
                ("signals", "palm_resource_invoked, palm_model_saved"),
            ],
        )
    )

    discovery = runtime.discovery
    if discovery is not None:
        discovery_rows: list[tuple[str, Any]] = [
            ("apps scanned", discovery.apps_scanned),
            ("definition modules", _format_list(discovery.definition_modules)),
            ("resource modules", _format_list(discovery.resource_modules)),
            ("commit handler modules", _format_list(discovery.commit_handler_modules)),
        ]
        if discovery.errors:
            for error in discovery.errors:
                report.issues.append(f"discovery: {error}")
            discovery_rows.append(("discovery errors", _format_list(discovery.errors)))
        report.sections.append(("Discovery", discovery_rows))

        if discovery.django_models:
            model_rows: list[tuple[str, Any]] = [
                ("provider", PROVIDER_NAME),
                ("models registered", len(discovery.django_models)),
            ]
            for model_label, config in list_registered_models():
                model_rows.append((model_label, ", ".join(config.normalized_actions())))
            model_rows.append(("resource definitions", len(discovery.django_model_resources)))
            report.sections.append(("Django Model Resources", model_rows))

    flows = app.list_flows()
    wizard_flows = [flow.name for flow in flows if flow.pattern == "wizard"]
    report.sections.append(
        (
            "Catalog",
            [
                ("flow definitions", len(flows)),
                ("wizard flows", ", ".join(wizard_flows) if wizard_flows else "(none)"),
                ("process definitions", len(app.list_processes())),
                ("resource definitions", len(app.list_resources())),
                ("process instances", len(app.list_instance_summaries())),
            ],
        )
    )

    report.sections.append(
        (
            "Effective PALM Settings (sample)",
            [
                (key, palm_config.get(key))
                for key in (
                    "storage_backend",
                    "host_profile",
                    "default_scheduler",
                    "load_example_definitions",
                    "enable_state_snapshot",
                )
            ],
        )
    )

    if storage_report["missing_tables"]:
        report.tips.append("Run `python manage.py migrate palm_django` to create ORM tables.")
    if not wizard_flows:
        report.tips.append(
            "Add a wizard flow with `step_kind: resource` and `resource_ref` pointing at "
            "your Django model resources (see tests/palm_sample/palm_definitions.py)."
        )
    if discovery is not None and not discovery.django_models:
        report.tips.append(
            "Decorate a model with `@as_palm_resource` or run `python manage.py palm quickstart`."
        )
    if report.ok:
        bind_host = palm_config.get("server_host", "127.0.0.1")
        bind_port = palm_config.get("server_port", 8080)
        report.tips.extend(
            [
                f"Run `python manage.py palm server` for Explorer at http://{bind_host}:{bind_port}/explorer",
                "Try `python manage.py palm flow list` to inspect registered flows.",
                "Try `python manage.py palm resource invoke <app.model.action> --state '{...}'`.",
                "Wrap multi-step work in `palm_atomic()` so Palm storage rolls back with Django.",
            ]
        )

    return report


def _format_list(values: list[str]) -> str:
    return ", ".join(values) if values else "(none)"


def _admin_status() -> str:
    try:
        from django.apps import apps as django_apps

        if not django_apps.is_installed("django.contrib.admin"):
            return "not installed (add django.contrib.admin to INSTALLED_APPS)"
        from django.contrib import admin

        from palm_django.models import (
            PalmDefinition,
            PalmProcessInstance,
            PalmStorageEntry,
        )

        registered = {
            PalmDefinition,
            PalmProcessInstance,
            PalmStorageEntry,
        }
        if all(model in admin.site._registry for model in registered):
            return "enabled (PalmDefinition, PalmProcessInstance, PalmStorageEntry)"
        return "partial registration"
    except Exception:
        return "unavailable"