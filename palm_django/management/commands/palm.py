"""
``python manage.py palm`` — Palm Engine management commands for Django projects.
"""

from __future__ import annotations

import argparse
from typing import Any

from django.core.management.base import BaseCommand, CommandError
from django.db import connection

from palm_django import __version__ as palm_django_version
from palm_django.runtime import bootstrap_palm, get_app, get_host, get_runtime, is_palm_started
from palm_django.settings import build_palm_settings_dict, get_django_integration_settings


class Command(BaseCommand):
    help = "Palm Engine commands (doctor, and more to come)."

    def add_arguments(self, parser: argparse.ArgumentParser) -> None:
        subparsers = parser.add_subparsers(dest="subcommand", required=True)

        doctor = subparsers.add_parser(
            "doctor",
            help="Health check and Django integration status report.",
        )
        doctor.add_argument(
            "--json",
            action="store_true",
            help="Emit machine-readable JSON (future; currently plain text).",
        )

    def handle(self, *args: Any, **options: Any) -> None:
        subcommand = options["subcommand"]
        if subcommand == "doctor":
            exit_code = self._run_doctor(json_output=options.get("json", False))
            if exit_code != 0:
                raise CommandError("Palm doctor found issues (see report above).")
            return
        raise CommandError(f"Unknown palm subcommand: {subcommand!r}")

    def _run_doctor(self, *, json_output: bool = False) -> int:
        if json_output:
            self.stdout.write(self.style.WARNING("--json is reserved for a future release."))

        from palm import __version__ as palm_version

        issues: list[str] = []
        if not is_palm_started():
            bootstrap_palm()
        if not is_palm_started():
            issues.append("ApplicationHost is not started")

        host = get_host()
        app = get_app()
        runtime = get_runtime()
        integration = get_django_integration_settings()
        palm_config = build_palm_settings_dict()

        storage = app.storage
        backend_name = storage.backend_name or "(none)"
        backend_open = storage.backend is not None and storage.backend.is_open

        if not backend_open:
            issues.append(f"Storage backend {backend_name!r} is not open")

        self.stdout.write("")
        self.stdout.write(self.style.MIGRATE_HEADING("Palm x Django - Doctor"))
        self.stdout.write("")

        self._section("Versions")
        self._kv("palm-django", palm_django_version)
        self._kv("palmengine", palm_version)
        self._kv("django", self._django_version())
        self._kv("database", connection.vendor)

        self._section("Runtime")
        self._kv("host started", "yes" if host.is_started else "no")
        self._kv("host roles", ", ".join(sorted(host.profile.roles)))
        self._kv("running runtimes", ", ".join(app.running()) or "(none)")
        self._kv("primary runtime", app.primary_name or "(none)")
        self._kv("storage backend", backend_name)
        self._kv("storage open", "yes" if backend_open else "no")

        self._section("Django Integration")
        self._kv("auto_start", integration["auto_start"])
        self._kv("discovery modules", ", ".join(integration["discovery_modules"]))
        self._kv("discover definitions", integration["discover_definitions"])
        self._kv("discover resources", integration["discover_resources"])
        self._kv("discover commit handlers", integration["discover_commit_handlers"])

        discovery = runtime.discovery
        if discovery is not None:
            self._section("Discovery")
            self._kv("apps scanned", discovery.apps_scanned)
            self._kv("definition modules", self._format_list(discovery.definition_modules))
            self._kv("resource modules", self._format_list(discovery.resource_modules))
            self._kv("commit handler modules", self._format_list(discovery.commit_handler_modules))
            if discovery.errors:
                for error in discovery.errors:
                    issues.append(f"discovery: {error}")
                self._kv("discovery errors", self._format_list(discovery.errors))

        self._section("Catalog")
        flows = app.list_flows()
        processes = app.list_processes()
        resources = app.list_resources()
        summaries = app.list_instance_summaries()
        self._kv("flow definitions", len(flows))
        self._kv("process definitions", len(processes))
        self._kv("resource definitions", len(resources))
        self._kv("process instances", len(summaries))

        self._section("Effective PALM Settings (sample)")
        for key in (
            "storage_backend",
            "host_profile",
            "default_scheduler",
            "load_example_definitions",
            "enable_state_snapshot",
        ):
            self._kv(key, palm_config.get(key))

        self.stdout.write("")
        if issues:
            self.stdout.write(self.style.ERROR(f"Found {len(issues)} issue(s):"))
            for issue in issues:
                self.stdout.write(self.style.ERROR(f"  • {issue}"))
            self.stdout.write("")
            return 1

        self.stdout.write(self.style.SUCCESS("All checks passed."))
        self.stdout.write("")
        return 0

    def _section(self, title: str) -> None:
        self.stdout.write(self.style.HTTP_INFO(f"[{title}]"))

    def _kv(self, key: str, value: Any) -> None:
        self.stdout.write(f"  {key}: {value}")

    @staticmethod
    def _format_list(values: list[str]) -> str:
        return ", ".join(values) if values else "(none)"

    @staticmethod
    def _django_version() -> str:
        import django

        return django.get_version()