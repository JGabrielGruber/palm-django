"""
``python manage.py palm`` — Palm Engine management commands for Django projects.
"""

from __future__ import annotations

import argparse
import json
from typing import Any

from django.core.management.base import BaseCommand, CommandError

from palm_django.doctor import build_doctor_report
from palm_django.management.palm_cli import (
    django_context_line,
    ensure_palm_runtime,
    parse_json_option,
    parse_key_value_pairs,
    resolve_flow_or_process,
    write_job_summary,
)
from palm_django.management.quickstart import run_quickstart
from palm_django.runtime import get_app, get_host


class Command(BaseCommand):
    help = "Palm Engine operator commands (doctor, quickstart, run, flow, instance, resource)."

    def add_arguments(self, parser: argparse.ArgumentParser) -> None:
        subparsers = parser.add_subparsers(dest="subcommand", required=True)

        doctor = subparsers.add_parser("doctor", help="Health check and integration status.")
        doctor.add_argument("--json", action="store_true", help="Emit the report as JSON.")

        quickstart = subparsers.add_parser(
            "quickstart",
            help="Show setup steps or generate sample model/resource snippets.",
        )
        quickstart.add_argument("--app", default="", help="Django app label to scaffold for.")
        quickstart.add_argument(
            "--write",
            action="store_true",
            help="Write palm_definitions.py for --app (fails if file exists).",
        )

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
            "quickstart": self._run_quickstart,
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

    def _run_quickstart(self, options: dict[str, Any]) -> None:
        run_quickstart(self, options)

    def _run_doctor(self, options: dict[str, Any]) -> None:
        report = build_doctor_report(django_version=self._django_version())

        if options.get("json"):
            payload = {
                "ok": report.ok,
                "issues": report.issues,
                "tips": report.tips,
                "sections": [
                    {"title": title, "rows": dict(rows)} for title, rows in report.sections
                ],
            }
            self.stdout.write(json.dumps(payload, indent=2, default=str))
            if not report.ok:
                raise CommandError("Palm doctor found issues (see JSON report).")
            return

        self.stdout.write("")
        self.stdout.write(self.style.MIGRATE_HEADING("Palm x Django — Doctor"))
        self.stdout.write("")

        for title, rows in report.sections:
            self._section(title)
            for key, value in rows:
                self._kv(key, value)

        self.stdout.write("")
        if report.issues:
            self.stdout.write(self.style.ERROR(f"Found {len(report.issues)} issue(s):"))
            for issue in report.issues:
                self.stdout.write(self.style.ERROR(f"  • {issue}"))
            if report.tips:
                self.stdout.write("")
                self.stdout.write(self.style.WARNING("Tips:"))
                for tip in report.tips:
                    self.stdout.write(self.style.WARNING(f"  → {tip}"))
            self.stdout.write("")
            raise CommandError("Palm doctor found issues (see report above).")

        self.stdout.write(self.style.SUCCESS("All checks passed — Palm x Django is ready."))
        if report.tips:
            self.stdout.write("")
            self.stdout.write(self.style.HTTP_INFO("Next steps:"))
            for tip in report.tips:
                self.stdout.write(f"  → {tip}")
        self.stdout.write("")

    def _section(self, title: str) -> None:
        self.stdout.write(self.style.HTTP_INFO(f"[{title}]"))

    def _kv(self, key: str, value: Any) -> None:
        self.stdout.write(f"  {key}: {value}")

    @staticmethod
    def _django_version() -> str:
        import django

        return django.get_version()

