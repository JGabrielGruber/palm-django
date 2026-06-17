"""
Shared helpers for ``manage.py palm`` subcommands.
"""

from __future__ import annotations

import json
from typing import Any

from django.core.management.base import BaseCommand, CommandError
from django.db import connection

from palm_django.runtime import bootstrap_palm, get_app, is_palm_started


def ensure_palm_runtime(command: BaseCommand) -> None:
    """Bootstrap Palm if needed; raise when the host cannot start."""
    if not is_palm_started():
        bootstrap_palm()
    if not is_palm_started():
        raise CommandError(
            "Palm ApplicationHost is not started. "
            "Run migrations and check `python manage.py palm doctor`."
        )


def django_context_line() -> str:
    """Short summary of the active Django database context."""
    db = connection.settings_dict
    name = db.get("NAME", "(unknown)")
    return f"{connection.vendor} / {name}"


def parse_json_option(raw: str | None, *, option_name: str) -> dict[str, Any]:
    if not raw:
        return {}
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise CommandError(f"Invalid JSON for {option_name}: {exc}") from exc
    if not isinstance(parsed, dict):
        raise CommandError(f"{option_name} must be a JSON object.")
    return parsed


def parse_key_value_pairs(pairs: list[str]) -> dict[str, str]:
    """Parse repeated ``key=value`` CLI tokens."""
    parsed: dict[str, str] = {}
    for item in pairs:
        if "=" not in item:
            raise CommandError(f"Expected key=value, got {item!r}")
        key, value = item.split("=", 1)
        parsed[key.strip()] = value.strip()
    return parsed


def resolve_flow_or_process(ref: str) -> tuple[str, str]:
    """Return ``('flow', ref)`` or ``('process', ref)`` based on the catalog."""
    app = get_app()
    flow_names = {flow.name for flow in app.list_flows()}
    flow_ids = {flow.definition_id for flow in app.list_flows()}
    if ref in flow_names or ref in flow_ids:
        return "flow", ref

    process_names = {process.name for process in app.list_processes()}
    process_ids = {process.definition_id for process in app.list_processes()}
    if ref in process_names or ref in process_ids:
        return "process", ref

    raise CommandError(
        f"Unknown flow or process {ref!r}. "
        "Use `python manage.py palm flow list` to see available flows."
    )


def write_job_summary(command: BaseCommand, job: Any, *, label: str) -> None:
    command.stdout.write(command.style.SUCCESS(f"{label} submitted"))
    command.stdout.write(f"  job_id: {job.id}")
    command.stdout.write(f"  status: {job.status.value}")
    instance_id = job.metadata.get("instance_id")
    if instance_id:
        command.stdout.write(f"  instance_id: {instance_id}")