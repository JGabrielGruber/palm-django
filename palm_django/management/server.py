"""
``palm server`` / ``palm host server`` — foreground ServerRuntime with Explorer.
"""

from __future__ import annotations

from typing import Any

from django.conf import settings as django_settings
from django.core.management.base import BaseCommand, CommandError

from palm_django.management.palm_cli import django_context_line
from palm_django.runtime import bootstrap_palm_server, shutdown_palm
from palm_django.settings import get_palm_settings


def resolve_server_bind(
    host: str | None = None,
    port: int | None = None,
) -> tuple[str, int]:
    """Resolve bind host/port from CLI overrides and ``PALM_*`` settings."""
    palm_settings = get_palm_settings()
    resolved_host = (host or "").strip() or palm_settings.server_host
    resolved_port = port if port is not None else palm_settings.server_port
    if resolved_port < 1 or resolved_port > 65535:
        raise CommandError(f"Invalid port {resolved_port!r}; expected 1-65535.")
    return resolved_host, resolved_port


def explorer_url(host: str, port: int) -> str:
    return f"http://{host}:{port}/explorer"


def add_server_arguments(parser: Any) -> None:
    parser.add_argument(
        "--host",
        default=None,
        help="Bind host (default: PALM_SERVER_HOST or 127.0.0.1).",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=None,
        help="Bind port (default: PALM_SERVER_PORT or 8080).",
    )


def run_palm_server(command: BaseCommand, options: dict[str, Any]) -> None:
    """Start ServerRuntime + Explorer using the Django-backed Palm host."""
    bind_host, bind_port = resolve_server_bind(options.get("host"), options.get("port"))
    url = explorer_url(bind_host, bind_port)

    try:
        host = bootstrap_palm_server(host=bind_host, port=bind_port)
    except Exception as exc:
        raise CommandError(f"Failed to start Palm server: {exc}") from exc

    command.stdout.write("")
    command.stdout.write(command.style.MIGRATE_HEADING("Palm x Django — Server"))
    command.stdout.write("")
    command.stdout.write(command.style.SUCCESS(f"Palm Explorer available at {url}"))
    command.stdout.write(f"  api base: http://{bind_host}:{bind_port}")
    command.stdout.write(f"  database: {django_context_line()}")
    command.stdout.write(f"  django debug: {django_settings.DEBUG}")
    command.stdout.write(f"  storage backend: {host.app.storage.backend_name or '(none)'}")
    command.stdout.write(f"  flows: {len(host.app.list_flows())}")
    command.stdout.write(f"  resources: {len(host.app.list_resources())}")
    command.stdout.write("")
    command.stdout.write("Press Ctrl+C to stop.")
    command.stdout.write("")

    try:
        host.run_until_signal()
    finally:
        shutdown_palm()
        command.stdout.write("")
        command.stdout.write(command.style.WARNING("Palm server stopped."))
        command.stdout.write("")