"""
``python manage.py palm`` — Palm Engine management commands for Django projects.
"""

from __future__ import annotations

import argparse
import json
from typing import Any

from django.core.management.base import BaseCommand, CommandError
from palm import __version__ as palm_version

from palm_django import __version__ as palm_django_version
from palm_django.backends import storage_health_report
from palm_django.management.palm_cli import (
    django_context_line,
    ensure_palm_runtime,
    parse_json_option,
    parse_key_value_pairs,
    resolve_flow_or_process,
    write_job_summary,
)
from palm_django.resources.registry import PROVIDER_NAME, list_registered_models
from palm_django.runtime import bootstrap_palm, get_app, get_host, get_runtime, is_palm_started
from palm_django.settings import build_palm_settings_dict, get_django_integration_settings


class Command(BaseCommand):
    help = "Palm Engine operator commands (doctor, run, flow, instance, resource)."

    def add_arguments(self, parser: argparse.ArgumentParser) -> None:
        subparsers = parser.add_subparsers(dest="subcommand", required=True)

        doctor = subparsers.add_parser("doctor", help="Health check and integration status.")
        doctor.add_argument("--json", action="store_true", help="Reserved for future JSON output.")

        run = subparsers.add_parser("run", help="Start a flow or process by name.")
        run.add_argument("ref", help="Flow or process name/id.")
        run.add_argument(
            "--kind",
            choices=("auto", "flow", "process"),
            default="auto",
            help="Force flow or process resolution (default: auto).",
        )
        run.add_argument("--metadata", default="", help="JSON metadata object for the job.")
        run.add_argument("--state", default="", help="JSON initial state object.")

        flow = subparsers.add_parser("flow", help="Flow definition commands.")
        flow_sub = flow.add_subparsers(dest="flow_command", required=True)
        flow_sub.add_parser("list", help="List registered flow definitions.")
        flow_start = flow_sub.add_parser("start", help="Start a flow by name or id.")
        flow_start.add_argument("ref", help="Flow name or id.")
        flow_start.add_argument("--metadata", default="", help="JSON metadata object.")
        flow_start.add_argument("--state", default="", help="JSON initial state object.")

        instance = subparsers.add_parser("instance", help="Process instance commands.")
        instance_sub = instance.add_subparsers(dest="instance_command", required=True)
        instance_list = instance_sub.add_parser("list", help="List process instances.")
        instance_list.add_argument(
            "--all",
            action="store_true",
            help="Include terminal instances.",
        )
        instance_resume = instance_sub.add_parser("resume", help="Resume a persisted instance.")
        instance_resume.add_argument("instance_id", help="Instance id to resume.")

        resource = subparsers.add_parser("resource", help="Resource definition commands.")
        resource_sub = resource.add_subparsers(dest="resource_command", required=True)
        resource_sub.add_parser("list", help="List resource definitions.")
        resource_invoke = resource_sub.add_parser("invoke", help="Invoke a resource by name.")
        resource_invoke.add_argument("ref", help="Resource definition name or id.")
        resource_invoke.add_argument("--state", default="", help="JSON state for param binding.")
        resource_invoke.add_argument(
            "--param",
            action="append",
            default=[],
            metavar="KEY=VALUE",
            help="Extra params (repeatable). Merged into state.",
        )
        resource_invoke.add_argument(
            "--provider",
            default="",
            help="Direct provider invoke (bypass definition), e.g. django_model.",
        )
        resource_invoke.add_argument("--action", default="", help="Action when using --provider.")

    def handle(self, *args: Any, **options: Any) -> None:
        subcommand = options["subcommand"]
        handlers = {
            "doctor": self._run_doctor,
            "run": self._run_run,
            "flow": self._run_flow,
            "instance": self._run_instance,
            "resource": self._run_resource,
        }
        handler = handlers.get(subcommand)
        if handler is None:
            raise CommandError(f"Unknown palm subcommand: {subcommand!r}")
        handler(options)

    def _run_run(self, options: dict[str, Any]) -> None:
        ensure_palm_runtime(self)
        host = get_host()
        ref = options["ref"]
        metadata = parse_json_option(options.get("metadata"), option_name="--metadata")
        state = parse_json_option(options.get("state"), option_name="--state")
        kind = options["kind"]

        if kind == "auto":
            resolved_kind, resolved_ref = resolve_flow_or_process(ref)
        elif kind == "flow":
            resolved_kind, resolved_ref = "flow", ref
        else:
            resolved_kind, resolved_ref = "process", ref

        if resolved_kind == "flow":
            job = host.submit_flow(resolved_ref, metadata=metadata, state=state or None)
        else:
            job = host.submit_process(resolved_ref, metadata=metadata, state=state or None)

        write_job_summary(self, job, label=resolved_kind.capitalize())
        self.stdout.write(f"  database: {django_context_line()}")

    def _run_flow(self, options: dict[str, Any]) -> None:
        ensure_palm_runtime(self)
        command = options["flow_command"]
        if command == "list":
            self._flow_list()
            return
        if command == "start":
            host = get_host()
            metadata = parse_json_option(options.get("metadata"), option_name="--metadata")
            state = parse_json_option(options.get("state"), option_name="--state")
            job = host.submit_flow(options["ref"], metadata=metadata, state=state or None)
            write_job_summary(self, job, label="Flow")
            return
        raise CommandError(f"Unknown flow command: {command!r}")

    def _flow_list(self) -> None:
        flows = get_app().list_flows()
        self.stdout.write(self.style.MIGRATE_HEADING(f"Flows ({len(flows)})"))
        if not flows:
            self.stdout.write("  (none)")
            return
        for flow in flows:
            schema = "schema" if flow.has_state_schema else "no schema"
            self.stdout.write(
                f"  {flow.name}  [{flow.pattern}]  id={flow.definition_id}  ({schema})"
            )

    def _run_instance(self, options: dict[str, Any]) -> None:
        ensure_palm_runtime(self)
        command = options["instance_command"]
        if command == "list":
            self._instance_list(include_all=options.get("all", False))
            return
        if command == "resume":
            job = get_host().resume_process(options["instance_id"])
            write_job_summary(self, job, label="Instance resume")
            return
        raise CommandError(f"Unknown instance command: {command!r}")

    def _instance_list(self, *, include_all: bool) -> None:
        terminal = {"SUCCEEDED", "FAILED", "CANCELLED"}
        summaries = get_app().list_instance_summaries()
        if not include_all:
            summaries = [item for item in summaries if item.status not in terminal]

        self.stdout.write(
            self.style.MIGRATE_HEADING(
                f"Instances ({len(summaries)}{'' if include_all else ', active only'})"
            )
        )
        if not summaries:
            self.stdout.write("  (none)")
            return
        for item in summaries:
            flow = item.flow_name or "-"
            process = item.process_name or "-"
            self.stdout.write(
                f"  {item.instance_id}  status={item.status}  flow={flow}  process={process}"
            )

    def _run_resource(self, options: dict[str, Any]) -> None:
        ensure_palm_runtime(self)
        command = options["resource_command"]
        if command == "list":
            self._resource_list()
            return
        if command == "invoke":
            self._resource_invoke(options)
            return
        raise CommandError(f"Unknown resource command: {command!r}")

    def _resource_list(self) -> None:
        resources = get_app().list_resources()
        self.stdout.write(self.style.MIGRATE_HEADING(f"Resources ({len(resources)})"))
        if not resources:
            self.stdout.write("  (none)")
            return
        for resource in resources:
            self.stdout.write(
                f"  {resource.name}  provider={resource.provider}  action={resource.action}"
            )

    def _resource_invoke(self, options: dict[str, Any]) -> None:
        app = get_app()
        state = parse_json_option(options.get("state"), option_name="--state")
        state.update(parse_key_value_pairs(options.get("param") or []))

        provider = (options.get("provider") or "").strip()
        action = (options.get("action") or "").strip()
        if provider:
            if not action:
                raise CommandError("--action is required when using --provider.")
            result = app.invoke_resource(provider=provider, action=action, params=state, state=state)
        else:
            result = app.invoke_resource(options["ref"], state=state)

        if not result.success:
            raise CommandError(result.error or "Resource invocation failed.")

        self.stdout.write(self.style.SUCCESS("Resource invoked successfully"))
        self.stdout.write(f"  provider: {result.metadata.get('provider', provider or '(definition)')}")
        self.stdout.write(f"  action: {result.metadata.get('action', action or '(definition)')}")
        self.stdout.write(f"  database: {django_context_line()}")
        self.stdout.write("  data:")
        self.stdout.write(json.dumps(result.data, indent=2, default=str))

    def _run_doctor(self, options: dict[str, Any]) -> None:
        if options.get("json"):
            self.stdout.write(self.style.WARNING("--json is reserved for a future release."))

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
        self._kv("database", django_context_line())

        self._section("Runtime")
        self._kv("host started", "yes" if host.is_started else "no")
        self._kv("host roles", ", ".join(sorted(host.profile.roles)))
        self._kv("running runtimes", ", ".join(app.running()) or "(none)")
        self._kv("primary runtime", app.primary_name or "(none)")
        self._kv("storage backend", backend_name)
        self._kv("storage open", "yes" if backend_open else "no")
        self._kv("storage durable", "yes" if backend_name == "django" else "no")

        storage_report = storage_health_report()
        self._section("Django ORM Storage")
        self._kv("tables ready", "yes" if storage_report["tables_ready"] else "no")
        if storage_report["missing_tables"]:
            for table in storage_report["missing_tables"]:
                issues.append(f"missing storage table: {table}")
            self._kv("missing tables", self._format_list(storage_report["missing_tables"]))
        counts = storage_report["counts"]
        if counts["definitions"] is not None:
            self._kv("orm definition rows", counts["definitions"])
            self._kv("orm instance rows", counts["instances"])
            self._kv("orm kv rows", counts["kv_entries"])

        self._section("Operator Tools")
        self._kv("management commands", "doctor, run, flow, instance, resource")
        self._kv("django admin", self._admin_status())

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
            if discovery.django_models:
                self._section("Django Model Resources")
                self._kv("provider", PROVIDER_NAME)
                self._kv("models registered", len(discovery.django_models))
                for model_label, config in list_registered_models():
                    self._kv(model_label, ", ".join(config.normalized_actions()))
                self._kv("resource definitions", len(discovery.django_model_resources))

        self._section("Catalog")
        self._kv("flow definitions", len(app.list_flows()))
        self._kv("process definitions", len(app.list_processes()))
        self._kv("resource definitions", len(app.list_resources()))
        self._kv("process instances", len(app.list_instance_summaries()))

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
            raise CommandError("Palm doctor found issues (see report above).")

        self.stdout.write(self.style.SUCCESS("All checks passed."))
        self.stdout.write("")

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

    @staticmethod
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